"""SQLAlchemy session dependency for FastAPI routes."""

from __future__ import annotations

from collections.abc import Generator
from os import environ

from sqlalchemy import create_engine
from sqlalchemy.orm import Session


def _sync_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def get_session() -> Generator[Session, None, None]:
    database_url = _sync_database_url(environ["DATABASE_URL"])
    engine = create_engine(database_url, future=True)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
