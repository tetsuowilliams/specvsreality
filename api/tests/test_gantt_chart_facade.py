"""Docker-backed integration tests for GanttChartFacade against the temporal schema."""

from __future__ import annotations

import os

# Ryuk can fail when Docker port publishing is flaky; containers still stop with pytest session end.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

from collections.abc import Generator
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from specvsreality_api.facades.gantt_chart_facade import (
    GanttChartFacade,
    create_gantt_chart_facade,
)
from specvsreality_repositories.repos import (
    BlobRepo,
    CommitFileRepo,
    CommitRepo,
    ImplementationClaimRepo,
    RepositoryRepo,
    RequirementRepo,
    RequirementVersionRepo,
    SpecRepo,
    SpecVersionRepo,
    Verdict,
)


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
def gantt_engine(pg_url: str) -> Generator[Engine, None, None]:
    database_url = _to_sync_url(pg_url)
    _upgrade_head(database_url)
    eng = create_engine(database_url)
    try:
        yield eng
    finally:
        eng.dispose()


@pytest.fixture()
def db_session(gantt_engine: Engine) -> Generator[Session, None, None]:
    connection = gantt_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def _seed_world(
    db_session: Session,
    *,
    versions: list[dict],
    code_paths_by_blob: dict[str, list[tuple[str, str]]] | None = None,
) -> dict[str, int | str]:
    """Seed a repo + one spec + one requirement with the supplied versions.

    Each ``versions`` entry is ``{"first_seen_at": datetime, "rv_content": str,
    "implements_blobs": list[str]}``. ``code_paths_by_blob`` maps a code blob
    to commits/paths it appeared at via ``commit_files``.
    """
    repository = RepositoryRepo(db_session).add(
        name="gf", url="https://example.test/gf.git"
    )
    spec = SpecRepo(db_session).get_or_create(
        repository_id=repository.id,
        name="paper-1",
        spec_path="specs/paper-1/spec.md",
        plan_path="specs/paper-1/plan.md",
        tasks_path="specs/paper-1/tasks.md",
    )
    req = RequirementRepo(db_session).get_or_create(
        spec_id=spec.id, external_id="REQ-1"
    )
    blobs = BlobRepo(db_session)
    commits = CommitRepo(db_session)
    sv_repo = SpecVersionRepo(db_session)
    rv_repo = RequirementVersionRepo(db_session)
    claim_repo = ImplementationClaimRepo(db_session)
    file_repo = CommitFileRepo(db_session)

    rv_ids: list[int] = []
    sv_ids: list[int] = []

    for index, version in enumerate(versions):
        first_seen_at = version["first_seen_at"]
        commit_sha = f"{index + 1}{'a' * 39}"[:40]
        commits.insert(
            sha=commit_sha,
            repository_id=repository.id,
            commit_date=first_seen_at,
        )
        spec_blob = f"{(index * 3) + 1:040x}"[:40].rjust(40, "0")
        plan_blob = f"{(index * 3) + 2:040x}"[:40].rjust(40, "0")
        tasks_blob = f"{(index * 3) + 3:040x}"[:40].rjust(40, "0")
        for sha in (spec_blob, plan_blob, tasks_blob):
            blobs.upsert(sha=sha, size_bytes=1)

        sv = sv_repo.insert(
            spec_id=spec.id,
            spec_blob_sha=spec_blob,
            plan_blob_sha=plan_blob,
            tasks_blob_sha=tasks_blob,
            first_seen_commit=commit_sha,
            first_seen_at=first_seen_at,
        )
        sv_ids.append(int(sv.id))

        rv = rv_repo.insert(
            requirement_id=req.id,
            spec_version_id=sv.id,
            content=version["rv_content"],
            content_hash=("0" * 40),
            extraction_model="m",
            extraction_prompt="p",
        )
        rv_ids.append(int(rv.id))

        for blob in version.get("implements_blobs", []):
            blobs.upsert(sha=blob, size_bytes=1)
            claim_repo.insert(
                requirement_version_id=rv.id,
                blob_sha=blob,
                verdict=Verdict.IMPLEMENTS.value,
                confidence=0.9,
                model_version="m1",
                prompt_version="p1",
                reasoning="ok",
            )

    if code_paths_by_blob:
        for blob_sha, locations in code_paths_by_blob.items():
            for commit_sha, path in locations:
                if not commits.exists(commit_sha):
                    commits.insert(
                        sha=commit_sha,
                        repository_id=repository.id,
                        commit_date=datetime(2026, 1, 1, tzinfo=UTC),
                    )
                blobs.upsert(sha=blob_sha, size_bytes=1)
                file_repo.insert_many(
                    commit_sha=commit_sha,
                    entries=[(path, blob_sha, None)],
                )

    return {
        "repo_id": int(repository.id),
        "spec_id": int(spec.id),
        "requirement_id": int(req.id),
        "rv_ids": rv_ids,
        "sv_ids": sv_ids,
    }


def test_gantt_meta_follows_last_requirement_segment(db_session: Session) -> None:
    code_blob = "9" * 40
    world = _seed_world(
        db_session,
        versions=[
            {
                "first_seen_at": datetime(2026, 3, 1, 12, 0, tzinfo=UTC),
                "rv_content": "v1",
                "implements_blobs": [],
            },
            {
                "first_seen_at": datetime(2026, 3, 10, 12, 0, tzinfo=UTC),
                "rv_content": "v2",
                "implements_blobs": [code_blob],
            },
        ],
        code_paths_by_blob={code_blob: [("a" * 40, "src/app.py")]},
    )

    facade = create_gantt_chart_facade(db_session)
    chart = facade.get_chart(
        repo_id=int(world["repo_id"]),
        spec_id=int(world["spec_id"]),
        now=datetime(2026, 4, 1, 12, 0, tzinfo=UTC),
    )

    assert chart.meta.requirement_implemented is True
    assert len(chart.requirement.history) == 2
    assert chart.requirement.history[0].status == "not_implemented"
    assert chart.requirement.history[1].status == "implemented"
    assert chart.requirement.history[0].requirement_text == "v1"
    assert chart.requirement.history[1].requirement_text == "v2"
    assert chart.requirement.history[0].commit is not None
    assert len(chart.requirement.history[0].commit) == 40

    assert len(chart.artifacts) == 1
    assert chart.artifacts[0].filepath == "src/app.py"
    art_seg = chart.artifacts[0].history[0]
    assert art_seg.blob_sha == code_blob
    assert art_seg.commit == "a" * 40


def test_get_requirement_latest_version_returns_newest_text(
    db_session: Session,
) -> None:
    world = _seed_world(
        db_session,
        versions=[
            {
                "first_seen_at": datetime(2026, 3, 1, tzinfo=UTC),
                "rv_content": "old",
                "implements_blobs": [],
            },
            {
                "first_seen_at": datetime(2026, 3, 10, tzinfo=UTC),
                "rv_content": "newest",
                "implements_blobs": [],
            },
        ],
    )
    facade = create_gantt_chart_facade(db_session)
    out = facade.get_requirement_latest_version(
        int(world["repo_id"]),
        int(world["spec_id"]),
        requirement_id=int(world["requirement_id"]),
    )
    assert out.requirement_text == "newest"
    assert out.paper_id == "REQ-1"


def test_get_requirement_latest_version_404_when_no_versions(
    db_session: Session,
) -> None:
    repository = RepositoryRepo(db_session).add(
        name="empty", url="https://example.test/empty.git"
    )
    spec = SpecRepo(db_session).get_or_create(
        repository_id=repository.id,
        name="empty-spec",
        spec_path="specs/empty-spec/spec.md",
        plan_path="specs/empty-spec/plan.md",
        tasks_path="specs/empty-spec/tasks.md",
    )
    req = RequirementRepo(db_session).get_or_create(
        spec_id=spec.id, external_id="R-EMPTY"
    )
    facade = create_gantt_chart_facade(db_session)
    with pytest.raises(HTTPException) as ei:
        facade.get_requirement_latest_version(
            int(repository.id), int(spec.id), requirement_id=int(req.id)
        )
    assert ei.value.status_code == 404


def test_no_requirement_returns_404(db_session: Session) -> None:
    repository = RepositoryRepo(db_session).add(
        name="nr", url="https://example.test/nr.git"
    )
    spec = SpecRepo(db_session).get_or_create(
        repository_id=repository.id,
        name="empty",
        spec_path="specs/empty/spec.md",
        plan_path="specs/empty/plan.md",
        tasks_path="specs/empty/tasks.md",
    )
    facade = create_gantt_chart_facade(db_session)
    with pytest.raises(HTTPException) as exc:
        facade.get_chart(repo_id=int(repository.id), spec_id=int(spec.id))
    assert exc.value.status_code == 404


def test_facade_unknown_spec_raises_404(db_session: Session) -> None:
    repository = RepositoryRepo(db_session).add(
        name="us", url="https://example.test/us.git"
    )
    facade = GanttChartFacade(db_session)
    with pytest.raises(HTTPException) as exc:
        facade.get_chart(repo_id=int(repository.id), spec_id=999999)
    assert exc.value.status_code == 404
