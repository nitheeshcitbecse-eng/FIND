from datetime import datetime, timezone

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai import face as face_ai
from ..ai import fingerprint as fp_ai
from ..ai import fusion
from ..ai import index as vindex
from ..ai import objects as obj_ai
from ..config import TOP_K
from ..database import get_db
from ..deps import audit, get_current_user, require_roles
from ..models import Candidate, Case, Evidence, MatchRun, ReferencePerson, User
from ..schemas import (
    CandidateOut,
    CaseBrief,
    CaseCreate,
    CaseOut,
    CaseUpdate,
    DecisionIn,
    EvidenceOut,
    MatchRunOut,
)
from ..storage import abs_path, save_upload

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

    rel = save_upload(file, f"cases/{case.case_number}/{kind}")
    path = str(abs_path(rel))

    quality: float | None = None
    extracted: dict = {}

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


def _detected_labels(case: Case) -> list[str]:
    labels: set[str] = set()
    for ev in case.evidence:
        if ev.kind in {"belonging", "other", "tattoo"} and ev.extracted:
            for label in ev.extracted.get("labels", []) or []:
                labels.add(label)
    return sorted(labels)


def _serialize_run(db: Session, run: MatchRun) -> MatchRunOut:
    candidates = []
    for cand in run.candidates:
        person = db.get(ReferencePerson, cand.person_id)
        if not person:
            continue
        candidates.append(
            CandidateOut(
                rank=cand.rank,
                score=cand.score,
                confidence=cand.confidence,
                person=person,
                explanation=cand.explanation or {},
            )
        )
    return MatchRunOut(
        run_id=run.id,
        case_id=run.case_id,
        created_at=run.created_at,
        engine_info=run.engine_info or {},
        candidates=candidates,
    )


@router.post("/{case_id}/match", response_model=MatchRunOut)
def run_match(
    case_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("officer", "verifier", "admin")),
):
    """Run the identification pipeline and return an explainable Top-K ranking.

    Synchronous for the prototype. For production, move the body into a Celery
    task and return a job id the app polls.
    """
    case = _get_case(db, case_id)
    if not case.evidence:
        raise HTTPException(400, "Add at least one piece of evidence before matching")

    face_emb, face_q, face_engine = _best_face_embedding(case)
    fp_template, fp_q = _best_fingerprint(case)
    labels = _detected_labels(case)

    # --- Candidate retrieval -------------------------------------------------
    # Face search narrows the gallery; without a face we fall back to a broader
    # scan (bounded, since 1:N fingerprint matching is expensive).
    shortlist: dict[int, float] = {}
    if face_emb:
        for pid, sim in vindex.search(db, face_emb, top_k=200):
            shortlist[pid] = sim

    if not shortlist:
        rows = db.query(ReferencePerson.id).order_by(ReferencePerson.id).limit(500).all()
        shortlist = {row[0] for row in rows}
        shortlist = {pid: 0.0 for pid in shortlist}

    persons = (
        db.query(ReferencePerson)
        .filter(ReferencePerson.id.in_(list(shortlist.keys())))
        .all()
    )

    # --- Per-candidate scoring ----------------------------------------------
    scored = []
    for person in persons:
        signals: dict[str, dict] = {}

        if fp_template and person.fingerprint_template:
            sim, good = fp_ai.match_templates(fp_template, person.fingerprint_template)
            signals["fingerprint"] = {
                "score": sim,
                "detail": f"{good} corresponding ridge features (probe quality {fp_q:.2f})",
            }

        if face_emb and person.face_embedding:
            sim = shortlist.get(person.id)
            if sim is None or sim == 0.0:
                sim = face_ai.cosine(face_emb, person.face_embedding)
            sim01 = max(0.0, (sim + 1.0) / 2.0) if sim < 0 else sim
            signals["face"] = {
                "score": sim01,
                "detail": f"cosine {sim:.3f} via {face_engine or 'face engine'} (photo quality {face_q:.2f})",
            }

        if case.tattoo_description and person.tattoo_description:
            sim = fusion.text_similarity(case.tattoo_description, person.tattoo_description)
            signals["tattoo"] = {
                "score": sim,
                "detail": f"case marks '{case.tattoo_description[:60]}' vs record '{person.tattoo_description[:60]}'",
            }

        if labels and person.known_belongings:
            sim = fusion.label_similarity(labels, person.known_belongings)
            signals["belongings"] = {
                "score": sim,
                "detail": f"detected {', '.join(labels[:5])}",
            }

        geo_score, dist = fusion.geo_similarity(
            case.found_lat, case.found_lng, person.last_known_lat, person.last_known_lng
        )
        if dist is not None:
            signals["geo"] = {
                "score": geo_score,
                "detail": f"{dist:.0f} km from last known location ({person.last_known_city or 'unknown'})",
            }

        demo_score, demo_detail = fusion.demographic_similarity(
            case.estimated_sex,
            case.estimated_age_min,
            case.estimated_age_max,
            person.sex,
            person.age,
        )
        if demo_detail != "no demographic data":
            signals["demographics"] = {"score": demo_score, "detail": demo_detail}

        if not signals:
            continue

        result = fusion.fuse(signals)
        scored.append((person, result, signals))

    if not scored:
        raise HTTPException(
            422,
            "No comparable records found. Check that reference records have "
            "face/fingerprint data enrolled (run seed.py).",
        )

    scored.sort(key=lambda item: item[1]["score"], reverse=True)
    top = scored[:TOP_K]
    runner_up = scored[1][1]["score"] if len(scored) > 1 else 0.0

    run = MatchRun(
        case_id=case.id,
        created_by_id=user.id,
        engine_info={
            "face": face_ai.engine_name(),
            "fingerprint": "opencv-gabor-orb",
            "objects": obj_ai.engine_name(),
            "retrieval": vindex.engine_name(),
            "fusion": "weighted-linear-v1",
            "gallery_size": len(persons),
        },
    )
    db.add(run)
    db.flush()

    for rank, (person, result, signals) in enumerate(top, start=1):
        margin = result["score"] - (runner_up if rank == 1 else 0.0)
        has_biometric = "fingerprint" in signals or "face" in signals
        band = fusion.confidence_band(
            result["score"], max(margin, 0.0), result["coverage"], has_biometric
        )
        explanation = {
            "components": result["components"],
            "coverage": result["coverage"],
            "margin_over_next": round(max(margin, 0.0), 4) if rank == 1 else None,
            "notes": fusion.build_notes(
                signals, result["coverage"], band, result["components"]
            ),
        }
        db.add(
            Candidate(
                match_run_id=run.id,
                person_id=person.id,
                rank=rank,
                score=result["score"],
                confidence=band,
                explanation=explanation,
            )
        )

    if case.status == "open":
        case.status = "matched"
    db.commit()
    db.refresh(run)

    audit(
        db, user, "run_match", "case", case_id,
        {"run_id": run.id, "top_score": top[0][1]["score"], "gallery": len(persons)},
    )
    return _serialize_run(db, run)


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
    return _serialize_run(db, run)


@router.post("/{case_id}/decision", response_model=CaseOut)
def record_decision(
    case_id: int,
    payload: DecisionIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("verifier", "admin")),
):
    """Record the human identification decision. Verifier/admin only."""
    case = _get_case(db, case_id)

    if payload.close_unidentified:
        case.status = "closed_unidentified"
        case.identified_person_id = None
    else:
        if payload.person_id is None:
            raise HTTPException(400, "person_id is required to confirm an identification")
        if not db.get(ReferencePerson, payload.person_id):
            raise HTTPException(404, "Reference person not found")
        case.identified_person_id = payload.person_id
        case.status = "identified"

    case.decision_note = payload.decision_note
    case.decided_by_id = user.id
    case.decided_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(case)

    audit(
        db, user, "record_decision", "case", case_id,
        {
            "status": case.status,
            "person_id": case.identified_person_id,
            "note": payload.decision_note,
        },
    )
    return case