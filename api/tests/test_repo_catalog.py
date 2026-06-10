"""Integration tests for repo catalog and spec tree routes (Postgres via testcontainers)."""

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
from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_commit_repo,
    create_git_repo_repo,
    create_implementation_at_commit_repo,
    create_implements_repo,
    create_spec_item_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus

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


def test_get_repo_catalog_lists_specs(catalog_client: TestClient, db_session: Session) -> None:
    gid = create_git_repo_repo(db_session).add(
        name="c1",
        url="https://example.test/c1.git",
        cursor_position="a" * 40,
        location="/tmp/c1",
    ).id
    create_spec_repo(db_session).add(paper_id="paper-1", repo_id=gid)

    cat = catalog_client.get(f"/repos/{gid}/catalog")
    assert cat.status_code == 200
    body = cat.json()
    assert len(body["specs"]) == 1
    assert body["specs"][0]["paper_id"] == "paper-1"
    assert "requirements" not in body["specs"][0]


def test_spec_tree_returns_versions_items_and_implementations(
    catalog_client: TestClient, db_session: Session
) -> None:
    gid = create_git_repo_repo(db_session).add(
        name="c2",
        url="https://example.test/c2.git",
        cursor_position="a" * 40,
        location="/tmp/c2",
    ).id
    commit = create_commit_repo(db_session).get_or_create(
        repo_id=gid,
        commit_sha=_COMMIT_SHA,
        commit_message="add feature",
        committed_at=_COMMIT_DT,
    )
    spec = create_spec_repo(db_session).add(paper_id="paper-2", repo_id=gid)
    version = create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        commit_id=commit.id,
        title="Title",
        summary="Summary",
        spec_md="# s",
        tasks_md="- t",
        plan_md="p",
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )
    item = create_spec_item_repo(db_session).add(
        spec_version_id=version.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="Greets users",
        source_quote="greets",
        importance=SpecItemImportance.MUST,
        success_criteria=["prints hello"],
        failure_criteria=["no output"],
    )
    implementation = create_implementation_at_commit_repo(db_session).upsert_evaluation(
        spec_item_id=item.id,
        commit_id=commit.id,
        implemented=True,
        summary="done",
        gaps=[],
        confidence=0.9,
    )
    artifact = create_artifact_repo(db_session).add(filepath="src/main.py")
    artifact_version = create_artifact_version_repo(db_session).add(
        artifact_id=artifact.id,
        commit_id=commit.id,
        status=VersionStatus.ACTIVE.value,
        file_content="print('hello')",
    )
    create_implements_repo(db_session).upsert_evidence(
        implementation_at_commit_id=implementation.id,
        artifact_version_id=artifact_version.id,
        evidence_file="src/main.py",
        evidence_line_number=1,
        evidence_snippet="print('hello')",
        evidence_relevance="prints greeting",
    )
    db_session.flush()

    resp = catalog_client.get(f"/repos/{gid}/specs/{spec.id}/tree")
    assert resp.status_code == 200
    body = resp.json()
    assert body["paper_id"] == "paper-2"
    assert len(body["versions"]) == 1
    version_body = body["versions"][0]
    assert version_body["title"] == "Title"
    assert version_body["commit_message"] == "add feature"
    assert len(version_body["items"]) == 1
    item_body = version_body["items"][0]
    assert item_body["local_key"] == "FR-1"
    assert item_body["item_type"] == "functional_behavior"
    assert item_body["importance"] == "must"
    assert item_body["success_criteria"] == ["prints hello"]
    assert len(item_body["implementations"]) == 1
    impl_body = item_body["implementations"][0]
    assert impl_body["implemented"] is True
    assert impl_body["confidence"] == 0.9
    assert len(impl_body["artifacts"]) == 1
    assert impl_body["artifacts"][0]["filepath"] == "src/main.py"
    assert impl_body["artifacts"][0]["evidence_line_number"] == 1


def test_catalog_unknown_repo_404(catalog_client: TestClient) -> None:
    r = catalog_client.get("/repos/999999999/catalog")
    assert r.status_code == 404


def test_spec_view_returns_latest_version_with_spans(
    catalog_client: TestClient, db_session: Session
) -> None:
    gid = create_git_repo_repo(db_session).add(
        name="view-repo",
        url="https://example.test/view.git",
        cursor_position="a" * 40,
        location="/tmp/view",
    ).id
    commit = create_commit_repo(db_session).get_or_create(
        repo_id=gid,
        commit_sha="d" * 40,
        commit_message="initial spec",
        committed_at=_COMMIT_DT,
    )
    spec = create_spec_repo(db_session).add(paper_id="paper-view", repo_id=gid)
    version = create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        commit_id=commit.id,
        title="Greeting spec",
        summary="Says hello",
        spec_md="# Greeting\n\nThe system shall greet users on startup.",
        tasks_md="- [ ] Greet users on startup",
        plan_md="## Plan\n\nImplement greeting on startup.",
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )
    create_spec_item_repo(db_session).add(
        spec_version_id=version.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="Greets users on startup",
        source_quote="greet users on startup",
        importance=SpecItemImportance.MUST,
        success_criteria=["prints hello"],
        failure_criteria=[],
    )
    db_session.flush()

    resp = catalog_client.get(f"/repos/{gid}/specs/{spec.id}/view")
    assert resp.status_code == 200
    body = resp.json()
    assert body["paper_id"] == "paper-view"
    assert body["version"]["commit_sha"] == "d" * 40
    assert "spec_md" not in body["version"]
    assert body["version"]["has_tasks_md"] is True
    assert body["version"]["has_plan_md"] is True
    assert body["summary"]["total_items"] == 1
    assert body["summary"]["status"] == "unknown"
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["local_key"] == "FR-1"
    assert item["spans"]["spec"] is not None
    assert item["spans"]["spec"]["start"] < item["spans"]["spec"]["end"]
    assert item["spans"]["tasks"] is not None
    assert item["spans"]["plan"] is not None

    markdown = catalog_client.get(f"/repos/{gid}/specs/{spec.id}/view/markdown")
    assert markdown.status_code == 200
    md_body = markdown.json()
    assert md_body["spec_md"].startswith("# Greeting")
    assert md_body["tasks_md"] is not None
    assert md_body["plan_md"] is not None


def test_spec_view_unknown_commit_404(catalog_client: TestClient, db_session: Session) -> None:
    gid = create_git_repo_repo(db_session).add(
        name="view-repo-2",
        url="https://example.test/view2.git",
        cursor_position="a" * 40,
        location="/tmp/view2",
    ).id
    spec = create_spec_repo(db_session).add(paper_id="paper-view-2", repo_id=gid)
    resp = catalog_client.get(
        f"/repos/{gid}/specs/{spec.id}/view",
        params={"commit_sha": "f" * 40},
    )
    assert resp.status_code == 404


def test_repo_dashboard_returns_summary_and_specs(
    catalog_client: TestClient, db_session: Session
) -> None:
    gid = create_git_repo_repo(db_session).add(
        name="dash-repo",
        url="https://example.test/dash.git",
        cursor_position="e" * 40,
        location="/tmp/dash",
    ).id
    commit = create_commit_repo(db_session).get_or_create(
        repo_id=gid,
        commit_sha="e" * 40,
        commit_message="initial",
        committed_at=_COMMIT_DT,
    )
    spec = create_spec_repo(db_session).add(paper_id="auth-flow", repo_id=gid)
    version = create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        commit_id=commit.id,
        title="Auth",
        summary="Login flow",
        spec_md="# Auth",
        tasks_md=None,
        plan_md=None,
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )
    item = create_spec_item_repo(db_session).add(
        spec_version_id=version.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="Users can log in",
        source_quote="log in",
        importance=SpecItemImportance.MUST,
        success_criteria=[],
        failure_criteria=[],
    )
    create_implementation_at_commit_repo(db_session).upsert_evaluation(
        spec_item_id=item.id,
        commit_id=commit.id,
        implemented=True,
        summary="done",
        gaps=[],
        confidence=0.95,
    )
    db_session.flush()

    resp = catalog_client.get(f"/repos/{gid}/dashboard")
    assert resp.status_code == 200
    body = resp.json()
    assert body["repo_name"] == "dash-repo"
    assert body["summary"]["specs_tracked"] == 1
    assert body["summary"]["coverage_percent"] == 100.0
    assert body["specs"][0]["status"] == "good"

    sidebar = catalog_client.get(f"/repos/{gid}/sidebar")
    assert sidebar.status_code == 200
    sidebar_spec = sidebar.json()["specs"][0]
    assert sidebar_spec["title"] == "Auth"
    assert len(sidebar_spec["versions"]) == 1
    assert sidebar_spec["versions"][0]["status"] == "good"


def test_repo_sidebar_lists_each_evaluation_commit(
    catalog_client: TestClient, db_session: Session
) -> None:
    gid = create_git_repo_repo(db_session).add(
        name="sidebar-multi-eval",
        url="https://example.test/sidebar.git",
        cursor_position="f" * 40,
        location="/tmp/sidebar",
    ).id
    commit_repo = create_commit_repo(db_session)
    earlier = commit_repo.get_or_create(
        repo_id=gid,
        commit_sha="a" * 40,
        commit_message="earlier",
        committed_at=datetime(2026, 1, 10, tzinfo=UTC),
    )
    later = commit_repo.get_or_create(
        repo_id=gid,
        commit_sha="b" * 40,
        commit_message="later",
        committed_at=datetime(2026, 1, 20, tzinfo=UTC),
    )
    spec = create_spec_repo(db_session).add(paper_id="specs/auth", repo_id=gid)
    version = create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        commit_id=earlier.id,
        title="Auth",
        summary="Login flow",
        spec_md="# Auth",
        tasks_md=None,
        plan_md=None,
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )
    item = create_spec_item_repo(db_session).add(
        spec_version_id=version.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="Users can log in",
        source_quote="log in",
        importance=SpecItemImportance.MUST,
        success_criteria=[],
        failure_criteria=[],
    )
    iac_repo = create_implementation_at_commit_repo(db_session)
    iac_repo.upsert_evaluation(
        spec_item_id=item.id,
        commit_id=earlier.id,
        implemented=True,
        summary="done",
        gaps=[],
        confidence=0.95,
    )
    iac_repo.upsert_evaluation(
        spec_item_id=item.id,
        commit_id=later.id,
        implemented=True,
        summary="still done",
        gaps=[],
        confidence=0.9,
    )
    db_session.flush()

    sidebar = catalog_client.get(f"/repos/{gid}/sidebar")
    assert sidebar.status_code == 200
    sidebar_spec = sidebar.json()["specs"][0]
    assert sidebar_spec["id"] == spec.id
    assert len(sidebar_spec["versions"]) == 2
    assert sidebar_spec["versions"][0]["commit_sha"] == "b" * 40
    assert sidebar_spec["versions"][1]["commit_sha"] == "a" * 40
    assert sidebar_spec["versions"][0]["version_id"] == version.id
    assert sidebar_spec["versions"][1]["version_id"] == version.id


def test_repo_dashboard_unknown_repo_404(catalog_client: TestClient) -> None:
    resp = catalog_client.get("/repos/999999999/dashboard")
    assert resp.status_code == 404


def test_spec_tree_wrong_repo_404(catalog_client: TestClient, db_session: Session) -> None:
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
    r = catalog_client.get(f"/repos/{g2}/specs/{spec.id}/tree")
    assert r.status_code == 404
