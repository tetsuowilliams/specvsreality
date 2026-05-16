"""Docker-backed integration tests for GanttChartFacade."""

from __future__ import annotations

import os

# Ryuk can fail when Docker port publishing is flaky; containers still stop with pytest session end.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from testcontainers.postgres import PostgresContainer

from specvsreality_api.facades.gantt_chart_facade import GanttChartFacade, create_gantt_chart_facade
from specvsreality_repositories.repos import (
    VersionStatus,
    create_artifact_repo,
    create_artifact_version_repo,
    create_git_repo_repo,
    create_implements_repo,
    create_requirement_repo,
    create_requirement_version_repo,
    create_spec_repo,
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


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return create_git_repo_repo(db_session).add(
        name="gantt-facade",
        url="https://example.test/gf.git",
        cursor_position="d" * 40,
        location="/tmp/gf",
    ).id


def test_gantt_meta_follows_last_requirement_segment(db_session: Session, git_row_id: int) -> None:
    ts0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    ts1 = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    now = datetime(2026, 4, 1, 12, 0, tzinfo=UTC)

    spec = create_spec_repo(db_session).add(paper_id="fr-001", repo_id=git_row_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="fr-001")
    rv1 = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_id="a" * 40,
        commit_datetime=ts0,
        requirement_text="v1",
        filepath_globs=["*.py"],
        status="open",
    )
    rv2 = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_id="b" * 40,
        commit_datetime=ts1,
        requirement_text="v2",
        filepath_globs=["*.py"],
        status="open",
    )
    art = create_artifact_repo(db_session).add(filepath="count.py")
    av_active = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id="a" * 40,
        commit_datetime=ts0,
        status=VersionStatus.ACTIVE.value,
        file_content="x",
    )
    av_inactive = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id="b" * 40,
        commit_datetime=ts1,
        status=VersionStatus.INACTIVE.value,
        file_content="y",
    )
    create_implements_repo(db_session).add(
        requirement_version_id=rv1.id,
        artifact_version_id=av_active.id,
    )
    create_implements_repo(db_session).add(
        requirement_version_id=rv2.id,
        artifact_version_id=av_inactive.id,
    )

    facade = create_gantt_chart_facade(db_session)
    chart = facade.get_chart(repo_id=git_row_id, spec_id=spec.id, now=now)

    assert chart.meta.requirement_implemented is False
    assert len(chart.requirement.history) == 2
    h0, h1 = chart.requirement.history
    assert h0.start == ts0 and h0.end == ts1 and h0.status == "implemented" and h0.commit is None
    assert h1.start == ts1 and h1.end == now and h1.status == "not_implemented"


def test_get_requirement_latest_version_returns_newest_text(db_session: Session, git_row_id: int) -> None:
    ts0 = datetime(2026, 3, 1, 12, 0, tzinfo=UTC)
    ts1 = datetime(2026, 3, 10, 12, 0, tzinfo=UTC)
    spec = create_spec_repo(db_session).add(paper_id="lv-001", repo_id=git_row_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="REQ-LV")
    create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_id="a" * 40,
        commit_datetime=ts0,
        requirement_text="old",
        filepath_globs=["*.py"],
        status="open",
    )
    create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_id="b" * 40,
        commit_datetime=ts1,
        requirement_text="newest",
        filepath_globs=["*.py"],
        status="open",
    )
    facade = create_gantt_chart_facade(db_session)
    out = facade.get_requirement_latest_version(git_row_id, spec.id, requirement_id=req.id)
    assert out.requirement_text == "newest"
    assert out.paper_id == "REQ-LV"
    assert out.commit_id == "b" * 40


def test_get_requirement_latest_version_404_when_no_versions(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="empty-req", repo_id=git_row_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="R-EMPTY")
    facade = create_gantt_chart_facade(db_session)
    with pytest.raises(HTTPException) as ei:
        facade.get_requirement_latest_version(git_row_id, spec.id, requirement_id=req.id)
    assert ei.value.status_code == 404


def test_artifacts_sorted_by_filepath_and_raw_status(db_session: Session, git_row_id: int) -> None:
    ts = datetime(2026, 3, 1, tzinfo=UTC)
    now = datetime(2026, 5, 1, tzinfo=UTC)
    spec = create_spec_repo(db_session).add(paper_id="p-sort", repo_id=git_row_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r1")
    rv = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        requirement_text="t",
        filepath_globs=["*.py"],
        status="open",
    )
    z = create_artifact_repo(db_session).add(filepath="zebra.py")
    a = create_artifact_repo(db_session).add(filepath="a.py")
    av_z = create_artifact_version_repo(db_session).add(
        artifact_id=z.id,
        commit_id="z" * 40,
        commit_datetime=ts,
        status=VersionStatus.ACTIVE.value,
        file_content="",
    )
    av_a1 = create_artifact_version_repo(db_session).add(
        artifact_id=a.id,
        commit_id="c" * 40,
        commit_datetime=ts,
        status=VersionStatus.ACTIVE.value,
        file_content="",
    )
    av_a2 = create_artifact_version_repo(db_session).add(
        artifact_id=a.id,
        commit_id="d" * 40,
        commit_datetime=ts + timedelta(hours=1),
        status=VersionStatus.DELETED.value,
        file_content="",
    )
    create_implements_repo(db_session).add(requirement_version_id=rv.id, artifact_version_id=av_z.id)
    create_implements_repo(db_session).add(requirement_version_id=rv.id, artifact_version_id=av_a1.id)

    facade = create_gantt_chart_facade(db_session)
    chart = facade.get_chart(repo_id=git_row_id, spec_id=spec.id, now=now)

    paths = [b.filepath for b in chart.artifacts]
    assert paths == ["a.py", "zebra.py"]

    a_block = chart.artifacts[0]
    assert len(a_block.history) == 2
    assert a_block.history[0].status == VersionStatus.ACTIVE.value
    assert a_block.history[1].status == VersionStatus.DELETED.value
    assert a_block.history[0].commit == av_a1.commit_id


def test_multiple_requirements_without_id_returns_400(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="p-multi", repo_id=git_row_id)
    create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r1")
    create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r2")

    facade = create_gantt_chart_facade(db_session)
    with pytest.raises(HTTPException) as exc:
        facade.get_chart(repo_id=git_row_id, spec_id=spec.id)
    assert exc.value.status_code == 400


def test_multiple_requirements_with_id_selects_requirement(db_session: Session, git_row_id: int) -> None:
    now = datetime(2026, 5, 1, tzinfo=UTC)
    spec = create_spec_repo(db_session).add(paper_id="p-pick", repo_id=git_row_id)
    r1 = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="alpha")
    r2 = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="beta")
    rv2 = create_requirement_version_repo(db_session).add(
        requirement_id=r2.id,
        commit_id="b" * 40,
        commit_datetime=datetime(2026, 3, 1, tzinfo=UTC),
        requirement_text="only on beta",
        filepath_globs=["*.py"],
        status="open",
    )
    art = create_artifact_repo(db_session).add(filepath="only_beta.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id="b" * 40,
        commit_datetime=datetime(2026, 3, 1, tzinfo=UTC),
        status=VersionStatus.ACTIVE.value,
        file_content="",
    )
    create_implements_repo(db_session).add(requirement_version_id=rv2.id, artifact_version_id=av.id)

    facade = create_gantt_chart_facade(db_session)
    chart = facade.get_chart(repo_id=git_row_id, spec_id=spec.id, requirement_id=r2.id, now=now)
    assert chart.requirement.paper_id == "beta"
    assert len(chart.artifacts) == 1
    assert chart.artifacts[0].filepath == "only_beta.py"

    chart_r1 = facade.get_chart(repo_id=git_row_id, spec_id=spec.id, requirement_id=r1.id, now=now)
    assert chart_r1.requirement.paper_id == "alpha"
    assert chart_r1.artifacts == []


def test_requirement_id_not_in_spec_returns_404(db_session: Session, git_row_id: int) -> None:
    spec_a = create_spec_repo(db_session).add(paper_id="sa", repo_id=git_row_id)
    spec_b = create_spec_repo(db_session).add(paper_id="sb", repo_id=git_row_id)
    req_b = create_requirement_repo(db_session).add(spec_id=spec_b.id, paper_id="rb")

    facade = create_gantt_chart_facade(db_session)
    with pytest.raises(HTTPException) as exc:
        facade.get_chart(repo_id=git_row_id, spec_id=spec_a.id, requirement_id=req_b.id)
    assert exc.value.status_code == 404


def test_spec_repo_mismatch_returns_404(db_session: Session, git_row_id: int) -> None:
    other_git = create_git_repo_repo(db_session).add(
        name="other",
        url="https://example.test/other.git",
        cursor_position="e" * 40,
        location="/tmp/o",
    ).id
    spec = create_spec_repo(db_session).add(paper_id="p-x", repo_id=git_row_id)
    create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")

    facade = create_gantt_chart_facade(db_session)
    with pytest.raises(HTTPException) as exc:
        facade.get_chart(repo_id=other_git, spec_id=spec.id)
    assert exc.value.status_code == 404


def test_no_requirement_returns_404(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="empty", repo_id=git_row_id)
    facade = create_gantt_chart_facade(db_session)
    with pytest.raises(HTTPException) as exc:
        facade.get_chart(repo_id=git_row_id, spec_id=spec.id)
    assert exc.value.status_code == 404


def test_meta_true_when_latest_segment_implemented(db_session: Session, git_row_id: int) -> None:
    ts0 = datetime(2026, 3, 1, tzinfo=UTC)
    ts1 = datetime(2026, 3, 10, tzinfo=UTC)
    now = datetime(2026, 4, 1, tzinfo=UTC)
    spec = create_spec_repo(db_session).add(paper_id="p-meta", repo_id=git_row_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    rv1 = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_id="a" * 40,
        commit_datetime=ts0,
        requirement_text="v1",
        filepath_globs=["*.py"],
        status="open",
    )
    rv2 = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_id="b" * 40,
        commit_datetime=ts1,
        requirement_text="v2",
        filepath_globs=["*.py"],
        status="open",
    )
    art = create_artifact_repo(db_session).add(filepath="f.py")
    av1 = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id="a" * 40,
        commit_datetime=ts0,
        status=VersionStatus.INACTIVE.value,
        file_content="",
    )
    av2 = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id="b" * 40,
        commit_datetime=ts1,
        status=VersionStatus.ACTIVE.value,
        file_content="",
    )
    create_implements_repo(db_session).add(requirement_version_id=rv1.id, artifact_version_id=av1.id)
    create_implements_repo(db_session).add(requirement_version_id=rv2.id, artifact_version_id=av2.id)

    facade = create_gantt_chart_facade(db_session)
    chart = facade.get_chart(repo_id=git_row_id, spec_id=spec.id, now=now)
    assert chart.meta.requirement_implemented is True
    assert chart.requirement.history[-1].status == "implemented"


def test_facade_unknown_spec_raises_404(db_session: Session, git_row_id: int) -> None:
    facade = GanttChartFacade(db_session)
    with pytest.raises(HTTPException) as exc:
        facade.get_chart(repo_id=git_row_id, spec_id=999999)
    assert exc.value.status_code == 404
