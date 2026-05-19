"""Shared pytest fixtures for repository integration tests."""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from specvsreality_repositories.repos import RepositoryRepo


def _to_sync_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _upgrade_head(database_url: str) -> None:
    root = Path(__file__).resolve().parents[1]
    ini_path = root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(root / "alembic"))
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def pg_url() -> Generator[str, None, None]:
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def engine(pg_url: str) -> Generator[Engine, None, None]:
    database_url = _to_sync_url(pg_url)
    _upgrade_head(database_url)
    db_engine = create_engine(database_url)
    try:
        yield db_engine
    finally:
        db_engine.dispose()


@pytest.fixture()
def db_session(engine: Engine) -> Generator[Session, None, None]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def repository_id(db_session: Session) -> int:
    """Create a tracked repository row for tests that need a parent FK."""
    row = RepositoryRepo(db_session).add(
        name="test-repo",
        url="https://example.test/repo.git",
        clone_location="/tmp/test-repo",
    )
    return int(row.id)
