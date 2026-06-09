"""Tests for `SpecVersionRepo`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_spec_repo, create_spec_version_repo
from specvsreality_repositories.repos.enums import VersionStatus

_COMMIT_DT = datetime(2026, 1, 15, tzinfo=UTC)


def _add_spec_version(
    repo,
    *,
    spec_id: int,
    commit_id: int,
    spec_md: str = "# S",
    tasks_md: str | None = "- T",
    plan_md: str | None = "P",
):
    return repo.add(
        spec_id=spec_id,
        commit_id=commit_id,
        title="Title",
        summary="Summary",
        spec_md=spec_md,
        tasks_md=tasks_md,
        plan_md=plan_md,
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )


def test_add_and_get_by_id(db_session: Session, git_repo_id: int, commit_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0001-sv", repo_id=git_repo_id)
    repo = create_spec_version_repo(db_session)
    row = _add_spec_version(repo, spec_id=spec.id, commit_id=commit_id)

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.spec_id == spec.id
    assert loaded.commit_id == commit_id
    assert loaded.title == "Title"
    assert loaded.summary == "Summary"
    assert loaded.spec_md == "# S"
    assert loaded.tasks_md == "- T"
    assert loaded.plan_md == "P"
    assert loaded.created_at == _COMMIT_DT
    assert loaded.status == VersionStatus.ACTIVE.value


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_spec_version_repo(db_session)
    assert repo.get_by_id(999_999_999) is None


def test_get_or_create_is_idempotent_for_spec_and_commit(
    db_session: Session,
    git_repo_id: int,
    commit_id: int,
) -> None:
    spec = create_spec_repo(db_session).add(paper_id="specs/feature", repo_id=git_repo_id)
    repo = create_spec_version_repo(db_session)

    first, created = repo.get_or_create(
        spec_id=spec.id,
        commit_id=commit_id,
        title="Title",
        summary="Summary",
        spec_md="# S",
        tasks_md=None,
        plan_md=None,
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )
    assert created is True

    second, created = repo.get_or_create(
        spec_id=spec.id,
        commit_id=commit_id,
        title="Other",
        summary="Other",
        spec_md="# other",
        tasks_md=None,
        plan_md=None,
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )
    assert created is False
    assert second.id == first.id
    assert second.spec_md == "# S"


def test_add_accepts_null_tasks_and_plan(
    db_session: Session, git_repo_id: int, commit_id: int
) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0002-null-sidecars", repo_id=git_repo_id)
    repo = create_spec_version_repo(db_session)
    row = _add_spec_version(repo, spec_id=spec.id, commit_id=commit_id, tasks_md=None, plan_md=None)

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.spec_md == "# S"
    assert loaded.tasks_md is None
    assert loaded.plan_md is None
