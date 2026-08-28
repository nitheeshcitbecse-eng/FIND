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


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_number: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # status: pending | under_investigation | completed | not_completed
    status: Mapped[str] = mapped_column(String(32), default="pending")

    found_location: Mapped[str] = mapped_column(String(256), default="")
    found_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    found_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    found_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    estimated_sex: Mapped[str] = mapped_column(String(16), default="unknown")
    estimated_age_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    estimated_age_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tattoo_description: Mapped[str] = mapped_column(Text, default="")
    notes: Mapped[str] = mapped_column(Text, default="")

    # References govern_db.GovPerson.id — a separate database/engine, so this
    # is a plain unenforced integer, never a real ForeignKey.
    identified_gov_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    identified_address: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    """One "Run identification" outcome: a single fingerprint+face comparison
    of a case's evidence against govern_db, resolving to matched/not-matched.

    There is no per-candidate ranking anymore — govern_db.GovPerson is
    compared exhaustively and only the single best-scoring record (if any,
    above IDENTIFY_MATCH_THRESHOLD) is kept.
    """

    __tablename__ = "match_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    case_id: Mapped[int] = mapped_column(ForeignKey("cases.id"), index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # "combined" = fingerprint+face case-level check (run_match); "fingerprint"
    # = the fingerprint-only quick-check (match_fingerprint). record_decision
    # and latest_match only ever consider "combined" rows as the case's
    # official identification outcome — a quick-check must never be
    # mistaken for, or accidentally confirmed as, that outcome.
    mode: Mapped[str] = mapped_column(String(16), default="combined")

    matched: Mapped[bool] = mapped_column(default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[str] = mapped_column(String(16), default="low")

    # References govern_db.GovPerson.id — a separate database/engine, so this
    # is a plain unenforced integer, never a real ForeignKey.
    gov_person_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Denormalized copy of GovPerson fields captured at match time, so
    # displaying/auditing a past result never needs a second govern_db query.
    gov_person_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    gov_person_photo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)

    engine_info: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    actor_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(64))
    entity: Mapped[str] = mapped_column(String(64), default="")
    entity_id: Mapped[str] = mapped_column(String(64), default="")
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)