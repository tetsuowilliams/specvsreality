"""Integration tests for repo catalog routes (Postgres via testcontainers)."""

from __future__ import annotations

import os
from collections.abc import Generator
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
    create_git_repo_repo,
    create_requirement_repo,
    create_spec_repo,
    create_spec_version_repo,
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


def test_get_repo_catalog_and_spec_detail(catalog_client: TestClient, db_session: Session) -> None:
    gid = create_git_repo_repo(db_session).add(
        name="c1",
        url="https://example.test/c1.git",
        cursor_position="a" * 40,
        location="/tmp/c1",
    ).id
    spec = create_spec_repo(db_session).add(paper_id="paper-1", repo_id=gid)
    create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="req-a")
    create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="req-b")
    create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        spec_md="# s",
        tasks_md="- t",
        plan_md="p",
    )
    create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        spec_md="# s2",
        tasks_md=None,
        plan_md=None,
    )

    cat = catalog_client.get(f"/repos/{gid}/catalog")
    assert cat.status_code == 200
    body = cat.json()
    assert len(body["specs"]) == 1
    assert body["specs"][0]["paper_id"] == "paper-1"
    assert len(body["specs"][0]["requirements"]) == 2

    detail = catalog_client.get(f"/repos/{gid}/specs/{spec.id}")
    assert detail.status_code == 200
    d = detail.json()
    assert d["paper_id"] == "paper-1"
    assert len(d["versions"]) == 2
    assert d["versions"][0]["spec_md"] == "# s"
    assert d["versions"][0]["tasks_md"] == "- t"
    assert d["versions"][0]["plan_md"] == "p"
    assert d["versions"][1]["spec_md"] == "# s2"
    assert d["versions"][1]["tasks_md"] is None
    assert d["versions"][1]["plan_md"] is None


def test_catalog_unknown_repo_404(catalog_client: TestClient) -> None:
    r = catalog_client.get("/repos/999999999/catalog")
    assert r.status_code == 404


def test_spec_detail_wrong_repo_404(catalog_client: TestClient, db_session: Session) -> None:
    g1 = create_git_repo_repo(db_session).add(
        name="g1",
        url="https://example.test/g1.git",
        cursor_position="b" * 40,
        location="/tmp/g1",
    ).id
    g2 = create_git_repo_repo(db_session).add(
        name="g2",
        url="https://example.test/g2.git",
        cursor_position="c" * 40,
        location="/tmp/g2",
    ).id
    spec = create_spec_repo(db_session).add(paper_id="p", repo_id=g1)
    r = catalog_client.get(f"/repos/{g2}/specs/{spec.id}")
    assert r.status_code == 404
