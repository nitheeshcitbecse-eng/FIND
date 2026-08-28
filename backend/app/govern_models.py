from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .govern_database import GovernBase


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class GovPerson(GovernBase):
    """A record in the government identity database (govern_db).

    Lives in a physically separate database from everything the app itself
    owns (normal_db, see database.py/models.py) — a different SQLAlchemy
    engine, connection, and file entirely. The only writer is
    seed_govern_db.py; no router ever creates, edits, or deletes rows here.

    GovPerson.id is its own independent autoincrement sequence, unrelated to
    any id space in normal_db. Any reference to a GovPerson from normal_db
    (see MatchRun.gov_person_id, Case.identified_gov_person_id) is a plain,
    unenforced integer — never a real ForeignKey, since SQLite/SQLAlchemy
    cannot enforce a constraint across two separate database connections.
    """

    __tablename__ = "gov_persons"

    id: Mapped[int] = mapped_column(primary_key=True)
    aadhaar_number: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), default="")
    address: Mapped[str] = mapped_column(Text, default="")

    face_photo_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    fingerprint_path: Mapped[str | None] = mapped_column(String(256), nullable=True)

    face_embedding: Mapped[list | None] = mapped_column(JSON, nullable=True)
    fingerprint_template: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
