"""SQLAlchemy session dependency for FastAPI routes."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_api.config import get_settings


def get_session() -> Generator[Session, None, None]:
    settings = get_settings()
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is required")
    database_url = settings.sync_database_url()
    engine = create_engine(database_url, future=True)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
