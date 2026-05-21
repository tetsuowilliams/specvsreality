"""Tests for GanttDataRepo read methods."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_gantt_data_repo,
    create_git_repo_repo,
    create_implements_repo,
    create_requirement_repo,
    create_requirement_version_repo,
    create_spec_repo,
)


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return create_git_repo_repo(db_session).add(
        name="gantt-data",
        url="https://example.test/gantt.git",
        cursor_position="c" * 40,
        location="/tmp/gantt",
    ).id


def test_list_requirements_for_spec_ordered(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="p1", repo_id=git_row_id)
    r1 = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="a")
    r2 = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="b")
    repo = create_gantt_data_repo(db_session)
    rows = repo.list_requirements_for_spec_ordered(spec_id=spec.id)
    assert [r.id for r in rows] == [r1.id, r2.id]


def test_list_requirement_versions_ordered(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="p2", repo_id=git_row_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    ts = datetime.now(UTC)
    v2 = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_sha="b" * 40,
        commit_datetime=ts + timedelta(hours=1),
        requirement_text="t2",
        filepath_globs=["*.py"],
        status="active",
    )
    v1 = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_sha="a" * 40,
        commit_datetime=ts,
        requirement_text="t1",
        filepath_globs=["*.py"],
        status="active",
    )
    repo = create_gantt_data_repo(db_session)
    rows = repo.list_requirement_versions_ordered(requirement_id=req.id)
    assert [r.id for r in rows] == [v1.id, v2.id]


def test_list_implements_with_artifact_versions(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="p3", repo_id=git_row_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    ts = datetime.now(UTC)
    rv = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_sha="a" * 40,
        commit_datetime=ts,
        requirement_text="t",
        filepath_globs=["*.py"],
        status="active",
    )
    art = create_artifact_repo(db_session).add(filepath="src/x.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_sha="a" * 40,
        commit_datetime=ts,
        status="active",
        file_content="x",
    )
    create_implements_repo(db_session).add(
        requirement_version_id=rv.id,
        artifact_version_id=av.id,
    )
    repo = create_gantt_data_repo(db_session)
    rows = repo.list_implements_with_artifact_versions(requirement_version_ids=[rv.id])
    assert len(rows) == 1
    impl, av2, art2 = rows[0]
    assert impl.requirement_version_id == rv.id
    assert impl.artifact_version_id == av.id
    assert av2.id == av.id
    assert art2.filepath == "src/x.py"


def test_list_implements_empty_ids(db_session: Session) -> None:
    repo = create_gantt_data_repo(db_session)
    assert repo.list_implements_with_artifact_versions(requirement_version_ids=[]) == []


def test_list_artifact_versions_for_artifact_ids_ordered(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="p4", repo_id=git_row_id)
    _ = spec
    art_a = create_artifact_repo(db_session).add(filepath="a.py")
    art_b = create_artifact_repo(db_session).add(filepath="b.py")
    ts = datetime.now(UTC)
    av_b1 = create_artifact_version_repo(db_session).add(
        artifact_id=art_b.id,
        commit_sha="1" * 40,
        commit_datetime=ts,
        status="active",
        file_content="",
    )
    av_a1 = create_artifact_version_repo(db_session).add(
        artifact_id=art_a.id,
        commit_sha="2" * 40,
        commit_datetime=ts,
        status="active",
        file_content="",
    )
    av_a2 = create_artifact_version_repo(db_session).add(
        artifact_id=art_a.id,
        commit_sha="3" * 40,
        commit_datetime=ts + timedelta(seconds=1),
        status="deleted",
        file_content="",
    )
    repo = create_gantt_data_repo(db_session)
    rows = repo.list_artifact_versions_for_artifact_ids_ordered(
        artifact_ids=[art_b.id, art_a.id],
    )
    # Repo orders by artifact_id asc, then commit time, not by the id list order.
    if art_a.id < art_b.id:
        expected_ids = [av_a1.id, av_a2.id, av_b1.id]
    else:
        expected_ids = [av_b1.id, av_a1.id, av_a2.id]
    assert [r.id for r in rows] == expected_ids
