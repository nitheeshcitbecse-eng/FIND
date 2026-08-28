from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai import face as face_ai
from ..ai import fingerprint as fp_ai
from ..ai import fusion
from ..ai import objects as obj_ai
from ..config import IDENTIFY_MATCH_THRESHOLD
from ..database import get_db
from ..deps import audit, get_current_user, require_roles
from ..govern_database import get_govern_db
from ..govern_models import GovPerson
from ..models import Case, Evidence, MatchRun, User
from ..schemas import (
    CaseBrief,
    CaseCreate,
    CaseOut,
    CaseUpdate,
    DecisionIn,
    EvidenceOut,
    MatchRunOut,
)
from ..storage import save_upload

router = APIRouter(prefix="/cases", tags=["cases"])

VALID_KINDS = {"face", "fingerprint", "tattoo", "belonging", "other"}


def _get_case(db: Session, case_id: int) -> Case:
    case = db.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return case


def _next_case_number(db: Session) -> str:
    year = datetime.now(timezone.utc).year
    count = db.query(Case).count() + 1
    return f"UBIS-{year}-{count:05d}"


@router.get("", response_model=list[CaseBrief])
def list_cases(
    status: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(Case)
    if status:
        query = query.filter(Case.status == status)
    return query.order_by(Case.id.desc()).limit(200).all()


@router.post("", response_model=CaseOut, status_code=201)
def create_case(
    payload: CaseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("officer", "verifier", "admin")),
):
    number = payload.case_number or _next_case_number(db)
    if db.query(Case).filter(Case.case_number == number).first():
        raise HTTPException(409, f"Case number '{number}' already exists")

    case = Case(
        case_number=number,
        found_location=payload.found_location,
        found_lat=payload.found_lat,
        found_lng=payload.found_lng,
        found_at=datetime.now(timezone.utc),
        estimated_sex=payload.estimated_sex,
        estimated_age_min=payload.estimated_age_min,
        estimated_age_max=payload.estimated_age_max,
        tattoo_description=payload.tattoo_description,
        notes=payload.notes,
        created_by_id=user.id,
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    audit(db, user, "create_case", "case", case.id, {"case_number": number})
    return case


@router.get("/{case_id}", response_model=CaseOut)
def get_case(
    case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return _get_case(db, case_id)


@router.patch("/{case_id}", response_model=CaseOut)
def update_case(
    case_id: int,
    payload: CaseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("officer", "verifier", "admin")),
):
    case = _get_case(db, case_id)
    if case.status == "identified":
        raise HTTPException(409, "Case already has a confirmed identification")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(case, field, value)
    db.commit()
    db.refresh(case)

    audit(db, user, "update_case", "case", case_id)
    return case


@router.post("/{case_id}/evidence", response_model=EvidenceOut, status_code=201)
def upload_evidence(
    case_id: int,
    kind: str = Form(...),
    label: str = Form(""),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("officer", "verifier", "admin")),
):
    case = _get_case(db, case_id)
    if kind not in VALID_KINDS:
        raise HTTPException(400, f"kind must be one of {sorted(VALID_KINDS)}")

    quality: float | None = None
    extracted: dict = {}

    with save_upload(file, f"cases/{case.case_number}/{kind}") as (rel, path):
        try:
            if kind == "face":
                result = face_ai.embed_face(path)
                quality = result["quality"]
                extracted = {
                    "engine": result["engine"],
                    "bbox": result["bbox"],
                    "faces_found": result["faces_found"],
                    "embedding": result["embedding"],
                }
            elif kind == "fingerprint":
                template = fp_ai.extract_template(path)
                quality = template["quality"]
                extracted = {"engine": "opencv-orb", "template": template}
            else:
                detected = obj_ai.detect_objects(path)
                extracted = detected
        except Exception as exc:  # noqa: BLE001
            extracted = {"error": str(exc)}

    evidence = Evidence(
        case_id=case.id,
        kind=kind,
        label=label,
        file_path=rel,
        quality_score=quality,
        extracted=extracted,
    )
    db.add(evidence)
    db.commit()
    db.refresh(evidence)

    audit(
        db, user, "upload_evidence", "case", case_id,
        {"evidence_id": evidence.id, "kind": kind, "quality": quality},
    )
    return evidence


@router.delete("/{case_id}/evidence/{evidence_id}", status_code=204)
def delete_evidence(
    case_id: int,
    evidence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("officer", "verifier", "admin")),
):
    evidence = db.get(Evidence, evidence_id)
    if not evidence or evidence.case_id != case_id:
        raise HTTPException(404, "Evidence not found for this case")
    db.delete(evidence)
    db.commit()
    audit(db, user, "delete_evidence", "case", case_id, {"evidence_id": evidence_id})


def _best_face_embedding(case: Case) -> tuple[list[float] | None, float, str]:
    best, best_q, engine = None, 0.0, ""
    for ev in case.evidence:
        if ev.kind != "face" or not ev.extracted:
            continue
        emb = ev.extracted.get("embedding")
        q = ev.quality_score or 0.0
        if emb and q >= best_q:
            best, best_q, engine = emb, q, ev.extracted.get("engine", "")
    return best, best_q, engine


def _best_fingerprint(case: Case) -> tuple[dict | None, float]:
    best, best_q = None, 0.0
    for ev in case.evidence:
        if ev.kind != "fingerprint" or not ev.extracted:
            continue
        template = ev.extracted.get("template")
        q = ev.quality_score or 0.0
        if template and q >= best_q:
            best, best_q = template, q
    return best, best_q


def _serialize_run(run: MatchRun) -> MatchRunOut:
    message = (
        f"Match found in the government database (score {run.score:.2f})."
        if run.matched
        else "No person found."
    )
    return MatchRunOut(
        run_id=run.id,
        case_id=run.case_id,
        created_at=run.created_at,
        matched=run.matched,
        address=run.address,
        score=run.score,
        confidence=run.confidence,
        message=message,
        engine_info=run.engine_info or {},
    )


@router.post("/{case_id}/match", response_model=MatchRunOut)
def run_match(
    case_id: int,
    db: Session = Depends(get_db),
    govdb: Session = Depends(get_govern_db),
    user: User = Depends(require_roles("officer", "verifier", "admin")),
):
    """Compare the case's fingerprint and/or face evidence against govern_db
    and record a single matched/not-matched verdict.

    Synchronous for the prototype. For production, move the body into a
    Celery task and return a job id the app polls.
    """
    case = _get_case(db, case_id)
    fp_template, fp_q = _best_fingerprint(case)
    face_emb, face_q, face_engine = _best_face_embedding(case)

    if not fp_template and not face_emb:
        raise HTTPException(
            400, "Add a fingerprint or face photo before running identification"
        )

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

        if fp_template and person.fingerprint_template:
            sim, good = fp_ai.match_templates(fp_template, person.fingerprint_template)
            signals["fingerprint"] = {
                "score": sim,
                "detail": f"{good} corresponding ridge features (probe quality {fp_q:.2f})",
            }

        if face_emb and person.face_embedding:
            sim = face_ai.cosine(face_emb, person.face_embedding)
            sim01 = max(0.0, (sim + 1.0) / 2.0) if sim < 0 else sim
            signals["face"] = {
                "score": sim01,
                "detail": f"cosine {sim:.3f} via {face_engine or 'face engine'} (photo quality {face_q:.2f})",
            }

        if not signals:
            continue

        result = fusion.fuse(signals)
        if result["score"] > best_score:
            best_score = result["score"]
            best_person = person

    matched = best_person is not None and best_score >= IDENTIFY_MATCH_THRESHOLD
    confidence = fusion.simple_confidence_band(best_score, IDENTIFY_MATCH_THRESHOLD)

    run = MatchRun(
        case_id=case.id,
        created_by_id=user.id,
        matched=matched,
        score=round(best_score, 4),
        confidence=confidence if matched else "low",
        gov_person_id=best_person.id if matched and best_person else None,
        address=best_person.address if matched and best_person else None,
        engine_info={
            "fingerprint": "opencv-gabor-orb",
            "face": face_ai.engine_name(),
            "fusion": "weighted-linear-v1",
            "gallery_size": len(gallery),
        },
    )
    db.add(run)

    if matched and case.status == "open":
        case.status = "matched"
    db.commit()
    db.refresh(run)

    audit(
        db, user, "run_match", "case", case_id,
        {"run_id": run.id, "matched": matched, "score": run.score, "gallery": len(gallery)},
    )
    return _serialize_run(run)


@router.get("/{case_id}/matches/latest", response_model=MatchRunOut)
def latest_match(
    case_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    _get_case(db, case_id)
    run = (
        db.query(MatchRun)
        .filter(MatchRun.case_id == case_id)
        .order_by(MatchRun.id.desc())
        .first()
    )
    if not run:
        raise HTTPException(404, "No match run for this case yet")
    return _serialize_run(run)


@router.post("/{case_id}/decision", response_model=CaseOut)
def record_decision(
    case_id: int,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("verifier", "admin")),
):
    """Record the human verifier's decision on the case's latest match.

    There is exactly one candidate to accept or reject — the single verdict
    from the most recent run_match — never a list to choose from.
    """
    case = _get_case(db, case_id)

    run = (
        db.query(MatchRun)
        .filter(MatchRun.case_id == case_id)
        .order_by(MatchRun.id.desc())
        .first()
    )
    if not run or not run.matched:
        raise HTTPException(400, "No match to confirm for this case")

    if payload.confirmed:
        case.status = "identified"
        case.identified_gov_person_id = run.gov_person_id
        case.identified_address = run.address
    else:
        case.status = "closed_unidentified"
        case.identified_gov_person_id = None
        case.identified_address = None

    case.decision_note = payload.decision_note
    case.decided_by_id = user.id
    case.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(case)

    audit(
        db, user, "record_decision", "case", case_id,
        {
            "status": case.status,
            "confirmed": payload.confirmed,
            "note": payload.decision_note,
        },
    )
    return case
