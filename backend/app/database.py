"""Database engine, session factory and table-creation helpers.

Supports PostgreSQL (production) and SQLite (local dev fallback) transparently
based on the DATABASE_URL setting.
"""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    # SQLite needs a special flag when used across threads (scheduler + API).
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    # Reasonable pool defaults for hosted Postgres.
    return {"pool_pre_ping": True, "pool_size": 5, "max_overflow": 10}


engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Safe to call repeatedly (no-op if they exist)."""
    # Import models so they register with the metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
