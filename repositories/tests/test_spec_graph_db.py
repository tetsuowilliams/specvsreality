"""Integration test for spec / requirement / artifact schema via repos."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_git_repo_repo,
    create_implements_repo,
    create_requirement_repo,
    create_requirement_version_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return create_git_repo_repo(db_session).add(
        name="g",
        url="https://example.test/g.git",
        cursor_position="b" * 40,
        location="/tmp/g",
    ).id


def test_spec_graph_round_trip(db_session: Session, git_row_id: int) -> None:
    paper_id = "0001-spec-graph"
    ts = datetime.now(UTC)

    spec = create_spec_repo(db_session).add(paper_id=paper_id, repo_id=git_row_id)
    create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        spec_md="# s",
        tasks_md="- t",
        plan_md="p",
    )
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id=paper_id)
    rv = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_id="c" * 40,
        commit_datetime=ts,
        requirement_text="do thing",
        filepath_globs=["*.py"],
        status="open",
    )
    art = create_artifact_repo(db_session).add(filepath="src/f.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id="c" * 40,
        commit_datetime=ts,
        status="present",
        file_content="x = 1",
    )
    impl = create_implements_repo(db_session).add(
        requirement_version_id=rv.id,
        artifact_version_id=av.id,
    )

    assert impl.requirement_version_id == rv.id
    assert impl.artifact_version_id == av.id
    assert create_spec_repo(db_session).get_by_id(spec.id) is not None


def test_requirement_repo_list_latest_active_for_spec(db_session: Session, git_row_id: int) -> None:
    ts = datetime.now(UTC)
    spec = create_spec_repo(db_session).add(paper_id="active-check", repo_id=git_row_id)

    requirement_repo = create_requirement_repo(db_session)
    requirement_version_repo = create_requirement_version_repo(db_session)

    req_active = requirement_repo.add(spec_id=spec.id, paper_id="r-active")
    requirement_version_repo.add(
        requirement_id=req_active.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        requirement_text="active requirement",
        filepath_globs=["*.py"],
        status=VersionStatus.ACTIVE.value,
    )

    req_inactive = requirement_repo.add(spec_id=spec.id, paper_id="r-inactive")
    requirement_version_repo.add(
        requirement_id=req_inactive.id,
        commit_id="b" * 40,
        commit_datetime=ts,
        requirement_text="was active",
        filepath_globs=["*.py"],
        status=VersionStatus.ACTIVE.value,
    )
    requirement_version_repo.add(
        requirement_id=req_inactive.id,
        commit_id="c" * 40,
        commit_datetime=ts + timedelta(seconds=1),
        requirement_text="now inactive",
        filepath_globs=["*.py"],
        status=VersionStatus.INACTIVE.value,
    )

    other_spec = create_spec_repo(db_session).add(paper_id="other-spec", repo_id=git_row_id)
    req_other_spec = requirement_repo.add(spec_id=other_spec.id, paper_id="r-other")
    requirement_version_repo.add(
        requirement_id=req_other_spec.id,
        commit_id="d" * 40,
        commit_datetime=ts,
        requirement_text="active but other spec",
        filepath_globs=["*.py"],
        status=VersionStatus.ACTIVE.value,
    )

    rows = requirement_repo.list_latest_active_for_spec(spec_id=spec.id)
    assert [row.id for row in rows] == [req_active.id]


def test_requirement_version_repo_list_latest_for_spec(db_session: Session, git_row_id: int) -> None:
    ts = datetime.now(UTC)
    spec = create_spec_repo(db_session).add(paper_id="latest-rv", repo_id=git_row_id)
    other_spec = create_spec_repo(db_session).add(paper_id="other-latest-rv", repo_id=git_row_id)

    requirement_repo = create_requirement_repo(db_session)
    requirement_version_repo = create_requirement_version_repo(db_session)

    req_a = requirement_repo.add(spec_id=spec.id, paper_id="a")
    requirement_version_repo.add(
        requirement_id=req_a.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        requirement_text="a v1",
        filepath_globs=["*.py"],
        status=VersionStatus.ACTIVE.value,
    )
    rv_a_latest = requirement_version_repo.add(
        requirement_id=req_a.id,
        commit_id="b" * 40,
        commit_datetime=ts + timedelta(seconds=10),
        requirement_text="a v2",
        filepath_globs=["src/**/*.py"],
        status=VersionStatus.ACTIVE.value,
    )

    req_b = requirement_repo.add(spec_id=spec.id, paper_id="b")
    requirement_version_repo.add(
        requirement_id=req_b.id,
        commit_id="c" * 40,
        commit_datetime=ts,
        requirement_text="b v1",
        filepath_globs=[],
        status=VersionStatus.INACTIVE.value,
    )

    req_other = requirement_repo.add(spec_id=other_spec.id, paper_id="other")
    requirement_version_repo.add(
        requirement_id=req_other.id,
        commit_id="d" * 40,
        commit_datetime=ts + timedelta(days=1),
        requirement_text="other only",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )

    latest = requirement_version_repo.list_latest(spec_id=spec.id)
    assert len(latest) == 2
    by_req = {row.requirement_id: row for row in latest}
    assert by_req[req_a.id].id == rv_a_latest.id
    assert by_req[req_a.id].requirement_text == "a v2"
    assert by_req[req_b.id].requirement_text == "b v1"
    assert req_other.id not in by_req


def test_requirement_version_repo_get_for_artifact_filepath(db_session: Session, git_row_id: int) -> None:
    ts = datetime.now(UTC)
    spec = create_spec_repo(db_session).add(paper_id="impl-match", repo_id=git_row_id)

    requirement_repo = create_requirement_repo(db_session)
    requirement_version_repo = create_requirement_version_repo(db_session)
    artifact_repo = create_artifact_repo(db_session)
    artifact_version_repo = create_artifact_version_repo(db_session)
    implements_repo = create_implements_repo(db_session)

    target_path = "src/pkg/mod.py"

    req_a = requirement_repo.add(spec_id=spec.id, paper_id="a")
    rv_a = requirement_version_repo.add(
        requirement_id=req_a.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        requirement_text="req a",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    req_b = requirement_repo.add(spec_id=spec.id, paper_id="b")
    rv_b = requirement_version_repo.add(
        requirement_id=req_b.id,
        commit_id="b" * 40,
        commit_datetime=ts,
        requirement_text="req b",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )

    art = artifact_repo.add(filepath=target_path)
    av = artifact_version_repo.add(
        artifact_id=art.id,
        commit_id="c" * 40,
        commit_datetime=ts,
        status="present",
        file_content="x = 1",
    )
    implements_repo.add(requirement_version_id=rv_a.id, artifact_version_id=av.id)
    implements_repo.add(requirement_version_id=rv_b.id, artifact_version_id=av.id)

    matches = requirement_version_repo.get_for_artifact_filepath(filepath=target_path, spec_id=spec.id)
    assert len(matches) == 2
    assert {m.requirement_id for m in matches} == {req_a.id, req_b.id}

    other_spec = create_spec_repo(db_session).add(paper_id="other-impl", repo_id=git_row_id)
    req_other = requirement_repo.add(spec_id=other_spec.id, paper_id="other")
    rv_other = requirement_version_repo.add(
        requirement_id=req_other.id,
        commit_id="d" * 40,
        commit_datetime=ts,
        requirement_text="other spec",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    art_other = artifact_repo.add(filepath=target_path)
    av_other = artifact_version_repo.add(
        artifact_id=art_other.id,
        commit_id="e" * 40,
        commit_datetime=ts,
        status="present",
        file_content="y = 2",
    )
    implements_repo.add(requirement_version_id=rv_other.id, artifact_version_id=av_other.id)

    scoped = requirement_version_repo.get_for_artifact_filepath(filepath=target_path, spec_id=spec.id)
    assert len(scoped) == 2
    assert rv_other.id not in {m.id for m in scoped}

    all_specs = requirement_version_repo.get_for_artifact_filepath(filepath=target_path, spec_id=None)
    assert len(all_specs) == 3
    assert {m.id for m in all_specs} == {rv_a.id, rv_b.id, rv_other.id}

    assert requirement_version_repo.get_for_artifact_filepath(filepath="vendor/missing.py", spec_id=spec.id) == []


def test_artifact_version_repo_get_latest_for_artifact_filepath(db_session: Session) -> None:
    ts = datetime.now(UTC)
    artifact_repo = create_artifact_repo(db_session)
    artifact_version_repo = create_artifact_version_repo(db_session)

    path = "src/lib.py"
    art = artifact_repo.add(filepath=path)
    av_old = artifact_version_repo.add(
        artifact_id=art.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        status="present",
        file_content="v1",
    )
    av_new = artifact_version_repo.add(
        artifact_id=art.id,
        commit_id="b" * 40,
        commit_datetime=ts + timedelta(seconds=30),
        status="present",
        file_content="v2",
    )

    latest = artifact_version_repo.get_latest_for_artifact_filepath(filepath=path)
    assert latest is not None
    assert latest.id == av_new.id
    assert latest.file_content == "v2"

    assert artifact_version_repo.get_latest_for_artifact_filepath(filepath="missing/nope.py") is None

    art_dup = artifact_repo.add(filepath=path)
    av_dup_newer = artifact_version_repo.add(
        artifact_id=art_dup.id,
        commit_id="c" * 40,
        commit_datetime=ts + timedelta(minutes=1),
        status="present",
        file_content="dup newer",
    )
    across_rows = artifact_version_repo.get_latest_for_artifact_filepath(filepath=path)
    assert across_rows is not None
    assert across_rows.id == av_dup_newer.id
