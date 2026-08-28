from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai import face as face_ai
from ..ai import fingerprint as fp_ai
from ..ai import fusion
from ..config import IDENTIFY_MATCH_THRESHOLD
from ..deps import audit, require_roles
from ..database import get_db
from ..govern_database import get_govern_db
from ..govern_models import GovPerson
from ..models import User
from ..schemas import FingerprintIdentifyResult
from ..storage import save_upload

router = APIRouter(prefix="/persons", tags=["identify"])


@router.post("/identify/fingerprint", response_model=FingerprintIdentifyResult)
def identify_by_fingerprint(
    fingerprint: UploadFile = File(...),
    face_photo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    govdb: Session = Depends(get_govern_db),
    user: User = Depends(require_roles("officer", "verifier", "admin")),
):
    """1:N lookup: does this fingerprint (optionally + face) belong to anyone
    in govern_db?

    Meant for a live capture handed off from an external fingerprint-capture
    app, not for browsing. Only the biometrics actually captured — fingerprint,
    and face if a photo is supplied — are compared against govern_db, the
    government identity database (a separate database, read-only from this
    app; see govern_models.py). On a match, the record's name, address, and
    photo are returned so the officer can visually confirm the identity.
    """
    with save_upload(fingerprint, "identify/fingerprints") as (_, fp_path):
        try:
            probe_fp = fp_ai.extract_template(fp_path)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(400, f"Could not process fingerprint image: {exc}") from exc

    if not probe_fp.get("descriptors_b64"):
        raise HTTPException(
            422, "No usable ridge features detected in this fingerprint image."
        )

    probe_face_emb = None
    face_engine = ""
    if face_photo is not None:
        with save_upload(face_photo, "identify/faces") as (_, face_path):
            try:
                face_result = face_ai.embed_face(face_path)
            except Exception as exc:  # noqa: BLE001
                raise HTTPException(400, f"Could not process face photo: {exc}") from exc
        probe_face_emb = face_result["embedding"]
        face_engine = face_result["engine"]

    gallery = (
        govdb.query(GovPerson)
        .filter(
            GovPerson.fingerprint_template.isnot(None)
            | GovPerson.face_embedding.isnot(None)
        )
        .all()
    )

    best_person: GovPerson | None = None
    best_score = 0.0

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

    matched = best_person is not None and best_score >= IDENTIFY_MATCH_THRESHOLD
    confidence = fusion.simple_confidence_band(best_score, IDENTIFY_MATCH_THRESHOLD)

    audit(
        db, user, "identify_fingerprint", "gov_person",
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
            name=None,
            address=None,
            photo_url=None,
            message="No person found.",
        )

    return FingerprintIdentifyResult(
        matched=True,
        confidence=confidence,
        score=round(best_score, 4),
        quality=probe_fp["quality"],
        name=best_person.name,
        address=best_person.address,
        photo_url=best_person.face_photo_path,
        message="Match found in the government database.",
    )
