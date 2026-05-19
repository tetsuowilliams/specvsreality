"""Postgres + Alembic fixtures for worker integration tests."""

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


def _to_sync_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _alembic_root() -> Path:
    """Resolve the ``repositories`` package alembic config from the worker tree."""
    workspace_root = Path(__file__).resolve().parents[3]
    return workspace_root / "repositories"


def _upgrade_head(database_url: str) -> None:
    """Run migrations without letting alembic reconfigure global logging.

    ``alembic/env.py`` calls ``fileConfig(config.config_file_name)`` when given
    an ini path, which clobbers handlers attached by pytest (notably the one
    that backs ``caplog``). Building :class:`Config` without an ini file leaves
    ``config_file_name`` unset, so ``env.py`` skips the logging reset and we
    only need to provide ``script_location`` ourselves.
    """
    root = _alembic_root()
    cfg = Config()
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
    """Per-test transactional session: rolls back on teardown for isolation."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
