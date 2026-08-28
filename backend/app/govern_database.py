from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import GOVERN_DATABASE_URL

connect_args = {"check_same_thread": False} if GOVERN_DATABASE_URL.startswith("sqlite") else {}
govern_engine = create_engine(GOVERN_DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
GovernSessionLocal = sessionmaker(bind=govern_engine, autoflush=False, autocommit=False)


class GovernBase(DeclarativeBase):
    pass


def get_govern_db():
    db = GovernSessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_govern_db():
    from . import govern_models  # noqa: F401  (registers tables)

    GovernBase.metadata.create_all(bind=govern_engine)
