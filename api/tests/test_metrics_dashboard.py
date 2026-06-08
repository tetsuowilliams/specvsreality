"""Integration tests for the global metrics dashboard route."""

from __future__ import annotations

import os
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
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
from specvsreality_repositories.models.enums import AgentName
from specvsreality_repositories.repos import (
    create_agent_run_metric_repo,
    create_commit_repo,
    create_git_repo_repo,
)

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
def metrics_engine(pg_url: str) -> Generator[Engine, None, None]:
    database_url = _to_sync_url(pg_url)
    _upgrade_head(database_url)
    eng = create_engine(database_url)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def db_session(metrics_engine: Engine) -> Generator[Session, None, None]:
    connection = metrics_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def metrics_client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    async def _noop_rabbit() -> None:
        return None

    def _session_override() -> Generator[Session, None, None]:
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[health.verify_rabbit_reachable] = _noop_rabbit
    app.dependency_overrides[get_session] = _session_override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_get_metrics_dashboard_aggregates_runs(metrics_client: TestClient, db_session: Session) -> None:
    git_repo = create_git_repo_repo(db_session).add(
        name="metrics-repo",
        url="https://example.test/metrics.git",
        cursor_position="a" * 40,
        location="/tmp/metrics",
    )
    commit = create_commit_repo(db_session).get_or_create(
        repo_id=git_repo.id,
        commit_sha="b" * 40,
        commit_message="scan",
        committed_at=datetime(2026, 6, 8, tzinfo=UTC),
    )
    metric_repo = create_agent_run_metric_repo(db_session)
    ran_at = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    metric_repo.record(
        repo_id=git_repo.id,
        commit_id=commit.id,
        agent=AgentName.SPEC_EXTRACTION,
        model="openai:gpt-4o-mini",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=Decimal("0.000450"),
        ran_at=ran_at,
    )
    metric_repo.record(
        repo_id=git_repo.id,
        commit_id=commit.id,
        agent=AgentName.IMPLEMENTS,
        model="openai:gpt-4o-mini",
        input_tokens=2000,
        output_tokens=1000,
        cost_usd=Decimal("0.000900"),
        ran_at=ran_at,
    )

    response = metrics_client.get("/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_runs"] == 2
    assert body["summary"]["total_tokens"] == 4500
    assert float(body["summary"]["total_cost_usd"]) == 0.00135
    assert len(body["by_repo"]) == 1
    assert body["by_repo"][0]["repo_name"] == "metrics-repo"
    assert len(body["by_agent"]) == 2
    assert len(body["recent_runs"]) == 2
    assert body["recent_runs"][0]["commit_sha"] == "b" * 40


def test_get_metrics_dashboard_filters_recent_runs_by_repo(
    metrics_client: TestClient,
    db_session: Session,
) -> None:
    repo_a = create_git_repo_repo(db_session).add(
        name="repo-a",
        url="https://example.test/a.git",
        cursor_position="a" * 40,
        location="/tmp/a",
    )
    repo_b = create_git_repo_repo(db_session).add(
        name="repo-b",
        url="https://example.test/b.git",
        cursor_position="c" * 40,
        location="/tmp/b",
    )
    commit_a = create_commit_repo(db_session).get_or_create(
        repo_id=repo_a.id,
        commit_sha="d" * 40,
        commit_message="a",
        committed_at=datetime(2026, 6, 8, tzinfo=UTC),
    )
    commit_b = create_commit_repo(db_session).get_or_create(
        repo_id=repo_b.id,
        commit_sha="e" * 40,
        commit_message="b",
        committed_at=datetime(2026, 6, 8, tzinfo=UTC),
    )
    metric_repo = create_agent_run_metric_repo(db_session)
    ran_at = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    for repo_id, commit_id in ((repo_a.id, commit_a.id), (repo_b.id, commit_b.id)):
        metric_repo.record(
            repo_id=repo_id,
            commit_id=commit_id,
            agent=AgentName.SPEC_EXTRACTION,
            model="openai:gpt-4o-mini",
            input_tokens=100,
            output_tokens=50,
            cost_usd=Decimal("0.000045"),
            ran_at=ran_at,
        )

    response = metrics_client.get(f"/metrics?repo_id={repo_a.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["summary"]["total_runs"] == 2
    assert len(body["recent_runs"]) == 1
    assert body["recent_runs"][0]["repo_name"] == "repo-a"
