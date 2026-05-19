"""Integration tests for repo catalog routes (Postgres via testcontainers)."""

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
from specvsreality_repositories.repos import (
    BlobRepo,
    CommitRepo,
    RepositoryRepo,
    RequirementRepo,
    SpecRepo,
    SpecVersionRepo,
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
def catalog_engine(pg_url: str) -> Generator[Engine, None, None]:
    database_url = _to_sync_url(pg_url)
    _upgrade_head(database_url)
    eng = create_engine(database_url)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def db_session(catalog_engine: Engine) -> Generator[Session, None, None]:
    connection = catalog_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def catalog_client(db_session: Session) -> Generator[TestClient, None, None]:
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


def _seed_spec_with_two_versions(
    db_session: Session,
) -> tuple[int, int]:
    """Create a repository + spec + two spec versions; return (repo_id, spec_id)."""
    repository = RepositoryRepo(db_session).add(
        name="c1", url="https://example.test/c1.git"
    )
    blobs = BlobRepo(db_session)
    blob_specs = ["a" * 40, "b" * 40, "c" * 40, "d" * 40, "e" * 40, "f" * 40]
    for sha in blob_specs:
        blobs.upsert(sha=sha, size_bytes=1)
    commits = CommitRepo(db_session)
    commit_one = "1" * 40
    commit_two = "2" * 40
    commits.insert(sha=commit_one, repository_id=repository.id, commit_date=datetime.now(UTC))
    commits.insert(sha=commit_two, repository_id=repository.id, commit_date=datetime.now(UTC))

    spec = SpecRepo(db_session).get_or_create(
        repository_id=repository.id,
        name="paper-1",
        spec_path="specs/paper-1/spec.md",
        plan_path="specs/paper-1/plan.md",
        tasks_path="specs/paper-1/tasks.md",
    )
    requirement_repo = RequirementRepo(db_session)
    requirement_repo.get_or_create(spec_id=spec.id, external_id="req-a")
    requirement_repo.get_or_create(spec_id=spec.id, external_id="req-b")
    sv_repo = SpecVersionRepo(db_session)
    sv_repo.insert(
        spec_id=spec.id,
        spec_blob_sha=blob_specs[0],
        plan_blob_sha=blob_specs[1],
        tasks_blob_sha=blob_specs[2],
        first_seen_commit=commit_one,
        first_seen_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    sv_repo.insert(
        spec_id=spec.id,
        spec_blob_sha=blob_specs[3],
        plan_blob_sha=blob_specs[4],
        tasks_blob_sha=blob_specs[5],
        first_seen_commit=commit_two,
        first_seen_at=datetime(2026, 2, 1, tzinfo=UTC),
    )
    return int(repository.id), int(spec.id)


def test_get_repo_catalog_and_spec_detail(
    catalog_client: TestClient, db_session: Session
) -> None:
    repo_id, spec_id = _seed_spec_with_two_versions(db_session)

    cat = catalog_client.get(f"/repos/{repo_id}/catalog")
    assert cat.status_code == 200
    body = cat.json()
    assert len(body["specs"]) == 1
    assert body["specs"][0]["paper_id"] == "paper-1"
    assert len(body["specs"][0]["requirements"]) == 2

    detail = catalog_client.get(f"/repos/{repo_id}/specs/{spec_id}")
    assert detail.status_code == 200
    d = detail.json()
    assert d["paper_id"] == "paper-1"
    assert len(d["versions"]) == 2
    assert d["versions"][0]["spec_blob_sha"] == "a" * 40
    assert d["versions"][1]["spec_blob_sha"] == "d" * 40


def test_catalog_unknown_repo_404(catalog_client: TestClient) -> None:
    r = catalog_client.get("/repos/999999999/catalog")
    assert r.status_code == 404


def test_spec_detail_wrong_repo_404(catalog_client: TestClient, db_session: Session) -> None:
    repo_a = RepositoryRepo(db_session).add(name="g1", url="https://example.test/g1.git")
    repo_b = RepositoryRepo(db_session).add(name="g2", url="https://example.test/g2.git")
    spec = SpecRepo(db_session).get_or_create(
        repository_id=repo_a.id,
        name="p",
        spec_path="specs/p/spec.md",
        plan_path="specs/p/plan.md",
        tasks_path="specs/p/tasks.md",
    )
    r = catalog_client.get(f"/repos/{repo_b.id}/specs/{spec.id}")
    assert r.status_code == 404
