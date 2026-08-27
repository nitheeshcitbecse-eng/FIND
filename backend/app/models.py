from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), default="")
    password_hash: Mapped[str] = mapped_column(String(256))
    # roles: officer | verifier | admin
    role: Mapped[str] = mapped_column(String(32), default="officer")
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReferencePerson(Base):
    """A record in the authorized identity database.

    In production this table is NOT yours — it is queried through an official
    government API. Here it stands in for that database so the pipeline is
    testable end to end.
    """

    __tablename__ = "reference_persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    record_ref: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    sex: Mapped[str] = mapped_column(String(16), default="unknown")
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_known_city: Mapped[str] = mapped_column(String(128), default="")
    last_known_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_known_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    address: Mapped[str] = mapped_column(Text, default="")
    tattoo_description: Mapped[str] = mapped_column(Text, default="")
    known_belongings: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    face_photo_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fingerprint_path: Mapped[str | None] = mapped_column(String(256), nullable=True)

    face_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fingerprint_template: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # status: open | matched | identified | closed_unidentified
    status: Mapped[str] = mapped_column(String(32), default="open")

    found_location: Mapped[str] = mapped_column(String(256), default="")
    found_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    found_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    found_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    estimated_sex: Mapped[str] = mapped_column(String(16), default="unknown")
    estimated_age_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_age_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tattoo_description: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    identified_person_id: Mapped[int | None] = mapped_column(
        ForeignKey("reference_persons.id"), nullable=True
    )
    decision_note: Mapped[str] = mapped_column(Text, default="")
    decided_by_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    evidence: Mapped[list["Evidence"]] = relationship(
        back_populates="case", cascade="all, delete-orphan", order_by="Evidence.id"
    )


class Evidence(Base):
    __tablename__ = "evidence"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"))
    # kind: face | fingerprint | tattoo | belonging | other
    kind: Mapped[str] = mapped_column(String(32))
    label: Mapped[str] = mapped_column(String(128), default="")
    file_path: Mapped[str] = mapped_column(String(256))
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    extracted: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case: Mapped[Case] = relationship(back_populates="evidence")


class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    engine_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    candidates: Mapped[list["Candidate"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Candidate.rank"
    )


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_run_id: Mapped[int] = mapped_column(ForeignKey("match_runs.id"))
    person_id: Mapped[int] = mapped_column(ForeignKey("reference_persons.id"))
    rank: Mapped[int] = mapped_column(Integer)
    score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(16), default="low")
    explanation: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    run: Mapped[MatchRun] = relationship(back_populates="candidates")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)