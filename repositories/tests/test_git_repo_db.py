"""Integration tests against real Postgres (Testcontainers)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from specvsreality_repositories.models.git_repo import GitRepo


def _upgrade_head(alembic_ini: Path) -> None:
    command.upgrade(Config(str(alembic_ini)), "head")


@pytest.fixture(scope="module")
def pg_url() -> str:
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


def test_migrations_apply_and_git_repo_round_trip(
    pg_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sync_url = pg_url
    if sync_url.startswith("postgresql+psycopg2://"):
        sync_url = sync_url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    elif sync_url.startswith("postgresql://"):
        sync_url = sync_url.replace("postgresql://", "postgresql+psycopg://", 1)
    monkeypatch.setenv("DATABASE_URL", sync_url)
    repo_root = Path(__file__).resolve().parents[1]
    alembic_ini = repo_root / "alembic.ini"
    _upgrade_head(alembic_ini)

    engine = create_engine(sync_url)
    rid = uuid.uuid4()
    with Session(engine) as session:
        row = GitRepo(
            id=rid,
            name="demo",
            url="https://example.com/repo.git",
            cursor_position="a" * 40,
            location="/data/repos/demo",
        )
        session.add(row)
        session.commit()

    with Session(engine) as session:
        found = session.scalars(select(GitRepo).where(GitRepo.id == rid)).one()
        assert found.name == "demo"
        assert found.cursor_position == "a" * 40
