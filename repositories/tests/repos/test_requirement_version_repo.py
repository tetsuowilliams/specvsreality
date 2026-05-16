"""Tests for `RequirementVersionRepo`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_requirement_repo,
    create_requirement_version_repo,
    create_spec_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus


def test_get_by_id_returns_row_after_add(db_session: Session, git_repo_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0001-rv", repo_id=git_repo_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    ts = datetime.now(UTC)
    repo = create_requirement_version_repo(db_session)
    row = repo.add(
        requirement_id=req.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        requirement_text="text",
        filepath_globs=["*.py"],
        status=VersionStatus.ACTIVE.value,
    )

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.requirement_id == req.id
    assert loaded.requirement_text == "text"


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_requirement_version_repo(db_session)
    assert repo.get_by_id(999_999_999) is None


def test_get_latest_for_requirement_returns_newest_by_commit_then_id(
    db_session: Session,
    git_repo_id: int,
) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0001-latest", repo_id=git_repo_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    ts = datetime.now(UTC)
    repo = create_requirement_version_repo(db_session)

    rv_old = repo.add(
        requirement_id=req.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        requirement_text="v1",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    rv_new = repo.add(
        requirement_id=req.id,
        commit_id="b" * 40,
        commit_datetime=ts + timedelta(seconds=5),
        requirement_text="v2",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )

    latest = repo.get_latest_for_requirement(requirement_id=req.id)
    assert latest is not None
    assert latest.id == rv_new.id
    assert latest.requirement_text == "v2"

    # Same commit time: higher id wins
    rv_tie_b = repo.add(
        requirement_id=req.id,
        commit_id="c" * 40,
        commit_datetime=rv_new.commit_datetime,
        requirement_text="tie-b",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    rv_tie_a = repo.add(
        requirement_id=req.id,
        commit_id="d" * 40,
        commit_datetime=rv_new.commit_datetime,
        requirement_text="tie-a",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    assert rv_tie_a.id > rv_tie_b.id
    latest2 = repo.get_latest_for_requirement(requirement_id=req.id)
    assert latest2 is not None
    assert latest2.id == rv_tie_a.id


def test_list_latest_without_spec_id_includes_requirements_across_specs(
    db_session: Session,
    git_repo_id: int,
) -> None:
    ts = datetime.now(UTC)
    spec1 = create_spec_repo(db_session).add(paper_id="0001-l1", repo_id=git_repo_id)
    spec2 = create_spec_repo(db_session).add(paper_id="0001-l2", repo_id=git_repo_id)
    req_repo = create_requirement_repo(db_session)
    rv_repo = create_requirement_version_repo(db_session)

    r1 = req_repo.add(spec_id=spec1.id, paper_id="p1")
    rv1 = rv_repo.add(
        requirement_id=r1.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        requirement_text="one",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    r2 = req_repo.add(spec_id=spec2.id, paper_id="p2")
    rv2 = rv_repo.add(
        requirement_id=r2.id,
        commit_id="b" * 40,
        commit_datetime=ts,
        requirement_text="two",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )

    all_latest = rv_repo.list_latest()
    ids = {row.id for row in all_latest}
    assert rv1.id in ids
    assert rv2.id in ids
