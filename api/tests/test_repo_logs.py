"""Integration tests for commit decision log routes."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from specvsreality_api.deps.session import get_session
from specvsreality_api.main import create_app
from specvsreality_api.routes import health
from specvsreality_repositories.models.enums import CommitLogAction
from specvsreality_repositories.repos import (
    create_commit_log_repo,
    create_commit_repo,
    create_git_repo_repo,
)

_COMMIT_SHA = "a" * 40
_COMMIT_DT = datetime(2026, 1, 15, tzinfo=UTC)

os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")


def _to_sync_url(url: str) -> str:
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _upgrade_head(database_url: str) -> None:
    repos_root = Path(__file__).resolve().parents[2] / "repositories"
    ini_path = repos_root / "alembic.ini"
    cfg = Config(str(ini_path))
    cfg.set_main_option("script_location", str(repos_root / "alembic"))
    os.environ["DATABASE_URL"] = database_url
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def pg_url() -> Generator[str, None, None]:
    with PostgresContainer("pgvector/pgvector:pg16") as postgres:
        yield postgres.get_connection_url()


@pytest.fixture(scope="session")
def logs_engine(pg_url: str) -> Generator[Engine, None, None]:
    database_url = _to_sync_url(pg_url)
    _upgrade_head(database_url)
    eng = create_engine(database_url)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def db_session(logs_engine: Engine) -> Generator[Session, None, None]:
    connection = logs_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def logs_client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    async def _noop_rabbit() -> None:
        return None

    def _session_override() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_session] = _session_override
    app.dependency_overrides[health.verify_rabbit_reachable] = _noop_rabbit
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_repo(db_session: Session) -> tuple[int, str]:
    repo = create_git_repo_repo(db_session).add(
        name="logs-repo",
        url="https://example.test/logs.git",
        cursor_position=_COMMIT_SHA,
        location="/tmp/logs",
    )
    commit = create_commit_repo(db_session).get_or_create(
        repo_id=repo.id,
        commit_sha=_COMMIT_SHA,
        commit_message="add auth spec",
        committed_at=_COMMIT_DT,
    )
    create_commit_log_repo(db_session).append(
        commit_id=commit.id,
        action=CommitLogAction.SPEC_EXTRACT.value,
        spec_folder="specs/auth",
        message="Launched spec extraction",
        reasoning="Spec folder touched in commit: specs/auth",
    )
    db_session.flush()
    return repo.id, _COMMIT_SHA


def test_logs_sidebar_lists_commits_with_counts(
    logs_client: TestClient,
    seeded_repo: tuple[int, str],
) -> None:
    repo_id, _ = seeded_repo
    response = logs_client.get(f"/repos/{repo_id}/logs/sidebar")
    assert response.status_code == 200
    body = response.json()
    assert len(body["commits"]) == 1
    assert body["commits"][0]["commit_sha"] == _COMMIT_SHA
    assert body["commits"][0]["commit_message"] == "add auth spec"
    assert body["commits"][0]["log_count"] == 1


def test_commit_logs_returns_entries(
    logs_client: TestClient,
    seeded_repo: tuple[int, str],
) -> None:
    repo_id, commit_sha = seeded_repo
    response = logs_client.get(f"/repos/{repo_id}/logs", params={"commit_sha": commit_sha})
    assert response.status_code == 200
    body = response.json()
    assert body["commit_sha"] == commit_sha
    assert len(body["logs"]) == 1
    assert body["logs"][0]["spec_folder"] == "specs/auth"
    assert body["logs"][0]["action"] == CommitLogAction.SPEC_EXTRACT.value
