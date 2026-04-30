"""Database engine, session factory, and init helper."""
from __future__ import annotations

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from config.settings import DATABASE_URL
from database.models import Base

# echo=False; flip to True locally for SQL debug
_engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create all tables. Idempotent."""
    Base.metadata.create_all(_engine)


def get_engine():
    return _engine


@contextmanager
def session_scope() -> Session:
    """Transactional context manager."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
