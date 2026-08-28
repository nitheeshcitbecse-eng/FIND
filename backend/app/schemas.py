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


class FingerprintIdentifyResult(BaseModel):
    matched: bool
    confidence: str
    score: float
    quality: float
    message: str
    name: str | None = None
    address: str | None = None
    photo_url: str | None = None


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
    identified_gov_person_id: int | None
    identified_address: str | None
    decision_note: str
    evidence: list[EvidenceOut] = []


class MatchRunOut(BaseModel):
    run_id: int
    case_id: int
    created_at: datetime
    matched: bool
    name: str | None
    address: str | None
    photo_url: str | None
    score: float
    confidence: str
    message: str
    engine_info: dict


class DecisionIn(BaseModel):
    confirmed: bool
    decision_note: str = ""