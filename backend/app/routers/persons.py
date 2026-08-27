from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai import face as face_ai
from ..ai import fingerprint as fp_ai
from ..ai import fusion
from ..ai import index as vindex
from ..config import IDENTIFY_MATCH_THRESHOLD
from ..database import get_db
from ..deps import audit, get_current_user, require_roles
from ..models import ReferencePerson, User
from ..schemas import FingerprintIdentifyResult, PersonBrief, PersonOut
from ..storage import abs_path, save_upload

router = APIRouter(prefix="/persons", tags=["reference-persons"])


@router.get("", response_model=list[PersonBrief])
def list_persons(
    q: str | None = None,
    limit: int = 50,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(ReferencePerson)
    if q:
        query = query.filter(ReferencePerson.name.ilike(f"%{q}%"))
    return query.order_by(ReferencePerson.id.desc()).limit(min(limit, 200)).all()


@router.get("/{person_id}", response_model=PersonOut)
def get_person(
    person_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    person = db.get(ReferencePerson, person_id)
    if not person:
        raise HTTPException(404, "Reference person not found")
    audit(db, user, "view_reference_person", "reference_person", person_id)
    return person


@router.post("", response_model=PersonOut, status_code=201)
def enroll_person(
    record_ref: str = Form(...),
    name: str = Form(...),
    sex: str = Form("unknown"),
    age: int | None = Form(None),
    last_known_city: str = Form(""),
    last_known_lat: float | None = Form(None),
    last_known_lng: float | None = Form(None),
    address: str = Form(""),
    tattoo_description: str = Form(""),
    known_belongings: str = Form(""),
    notes: str = Form(""),
    face_photo: UploadFile | None = File(None),
    fingerprint: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("admin")),
):
    """Enroll a record into the stand-in identity database (admin only).

    In production this data lives in the government system and is queried
    through an authorized API instead of being enrolled here.
    """
    if db.query(ReferencePerson).filter(ReferencePerson.record_ref == record_ref).first():
        raise HTTPException(409, f"record_ref '{record_ref}' already exists")

    person = ReferencePerson(
        record_ref=record_ref,
        name=name,
        sex=sex,
        age=age,
        last_known_city=last_known_city,
        last_known_lat=last_known_lat,
        last_known_lng=last_known_lng,
        address=address,
        tattoo_description=tattoo_description,
        known_belongings=known_belongings,
        notes=notes,
    )

    if face_photo is not None:
        rel = save_upload(face_photo, "reference/faces")
        person.face_photo_path = rel
        result = face_ai.embed_face(str(abs_path(rel)))
        person.face_embedding = result["embedding"]

    if fingerprint is not None:
        rel = save_upload(fingerprint, "reference/fingerprints")
        person.fingerprint_path = rel
        person.fingerprint_template = fp_ai.extract_template(str(abs_path(rel)))

    db.add(person)
    db.commit()
    db.refresh(person)

    vindex.invalidate()
    audit(db, user, "enroll_reference_person", "reference_person", person.id, {"name": name})
    return person


@router.post("/identify/fingerprint", response_model=FingerprintIdentifyResult)
def identify_by_fingerprint(
    fingerprint: UploadFile = File(...),
    face_photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("officer", "verifier", "admin")),
):
    """1:N lookup: does this fingerprint (optionally + face) belong to anyone
    in the reference DB?

    Meant for a live capture handed off from an external fingerprint-capture
    app, not for browsing. Only the biometrics actually captured from the
    person — fingerprint, and face if a photo is supplied — are compared.
    Soft attributes on a record (tattoos, belongings, last-known location,
    demographics) are never used here: those exist for the fuzzy case
    pipeline in cases.py, where you only have partial clues, not for a direct
    identity check against a government-grade biometric.
    """
    fp_rel = save_upload(fingerprint, "identify/fingerprints")
    try:
        probe_fp = fp_ai.extract_template(str(abs_path(fp_rel)))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, f"Could not process fingerprint image: {exc}") from exc

    if not probe_fp.get("descriptors_b64"):
        raise HTTPException(
            422, "No usable ridge features detected in this fingerprint image."
        )

    probe_face_emb = None
    face_engine = ""
    if face_photo is not None:
        face_rel = save_upload(face_photo, "identify/faces")
        try:
            face_result = face_ai.embed_face(str(abs_path(face_rel)))
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"Could not process face photo: {exc}") from exc
        probe_face_emb = face_result["embedding"]
        face_engine = face_result["engine"]

    gallery = (
        db.query(ReferencePerson)
        .filter(
            ReferencePerson.fingerprint_template.isnot(None)
            | ReferencePerson.face_embedding.isnot(None)
        )
        .all()
    )

    best_person: ReferencePerson | None = None
    best_score = 0.0
    best_components: list[dict] = []

    for person in gallery:
        signals: dict[str, dict] = {}

        if person.fingerprint_template:
            sim, good = fp_ai.match_templates(probe_fp, person.fingerprint_template)
            signals["fingerprint"] = {
                "score": sim,
                "detail": f"{good} corresponding ridge features",
            }

        if probe_face_emb and person.face_embedding:
            sim = face_ai.cosine(probe_face_emb, person.face_embedding)
            sim01 = max(0.0, (sim + 1.0) / 2.0) if sim < 0 else sim
            signals["face"] = {
                "score": sim01,
                "detail": f"cosine {sim:.3f} via {face_engine}",
            }

        if not signals:
            continue

        result = fusion.fuse(signals)
        if result["score"] > best_score:
            best_score = result["score"]
            best_person = person
            best_components = result["components"]

    matched = best_person is not None and best_score >= IDENTIFY_MATCH_THRESHOLD
    if best_score >= 0.75:
        confidence = "high"
    elif best_score >= IDENTIFY_MATCH_THRESHOLD:
        confidence = "medium"
    else:
        confidence = "low"

    audit(
        db, user, "identify_fingerprint", "reference_person",
        best_person.id if matched and best_person else "",
        {
            "score": round(best_score, 4),
            "matched": matched,
            "gallery_size": len(gallery),
            "used_face": probe_face_emb is not None,
        },
    )

    if not matched:
        return FingerprintIdentifyResult(
            matched=False,
            confidence="low",
            score=round(best_score, 4),
            quality=probe_fp["quality"],
            components=best_components,
            person=None,
            message="No matching record found for this fingerprint.",
        )

    return FingerprintIdentifyResult(
        matched=True,
        confidence=confidence,
        score=round(best_score, 4),
        quality=probe_fp["quality"],
        components=best_components,
        person=best_person,
        message=f"Matched to {best_person.name} ({best_person.record_ref}).",
    )