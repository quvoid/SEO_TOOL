"""
db.py — SQLAlchemy engine, session factory, and FastAPI dependency.
"""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .settings import get_settings

_settings = get_settings()


def _normalize_db_url(url: str) -> str:
    """
    Railway/Heroku/Neon hand out 'postgres://' or 'postgresql://' URLs, but our
    driver is psycopg3 which needs the '+psycopg' dialect. Normalize so the same
    env var works locally (SQLite) and in production (managed Postgres).
    """
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return url


engine = create_engine(_normalize_db_url(_settings.database_url), pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
