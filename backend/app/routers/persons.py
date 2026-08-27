from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..ai import face as face_ai
from ..ai import fingerprint as fp_ai
from ..ai import index as vindex
from ..database import get_db
from ..deps import audit, get_current_user, require_roles
from ..models import ReferencePerson, User
from ..schemas import PersonBrief, PersonOut
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