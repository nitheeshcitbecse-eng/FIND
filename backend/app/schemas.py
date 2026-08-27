from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    role: str


class PersonBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    record_ref: str
    name: str
    sex: str
    age: int | None
    last_known_city: str
    face_photo_path: str | None


class PersonOut(PersonBrief):
    tattoo_description: str
    known_belongings: str
    notes: str
    fingerprint_path: str | None


class CaseCreate(BaseModel):
    case_number: str | None = None
    found_location: str = ""
    found_lat: float | None = None
    found_lng: float | None = None
    estimated_sex: str = "unknown"
    estimated_age_min: int | None = None
    estimated_age_max: int | None = None
    tattoo_description: str = ""
    notes: str = ""


class CaseUpdate(BaseModel):
    found_location: str | None = None
    found_lat: float | None = None
    found_lng: float | None = None
    estimated_sex: str | None = None
    estimated_age_min: int | None = None
    estimated_age_max: int | None = None
    tattoo_description: str | None = None
    notes: str | None = None


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    kind: str
    label: str
    file_path: str
    quality_score: float | None
    extracted: dict | None
    created_at: datetime


class CaseBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    case_number: str
    status: str
    found_location: str
    created_at: datetime


class CaseOut(CaseBrief):
    found_lat: float | None
    found_lng: float | None
    estimated_sex: str
    estimated_age_min: int | None
    estimated_age_max: int | None
    tattoo_description: str
    notes: str
    identified_person_id: int | None
    decision_note: str
    evidence: list[EvidenceOut] = []


class CandidateOut(BaseModel):
    rank: int
    score: float
    confidence: str
    person: PersonBrief
    explanation: dict


class MatchRunOut(BaseModel):
    run_id: int
    case_id: int
    created_at: datetime
    engine_info: dict
    candidates: list[CandidateOut]


class DecisionIn(BaseModel):
    person_id: int | None = None
    decision_note: str = ""
    close_unidentified: bool = False