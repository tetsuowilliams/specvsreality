"""Tests for `SpecVersionRepo`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_spec_repo, create_spec_version_repo


def test_add_and_get_by_id(db_session: Session, git_repo_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0001-sv", repo_id=git_repo_id)
    repo = create_spec_version_repo(db_session)
    row = repo.add(spec_id=spec.id, spec_md="# S", tasks_md="- T", plan_md="P")

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.spec_id == spec.id
    assert loaded.spec_md == "# S"
    assert loaded.tasks_md == "- T"
    assert loaded.plan_md == "P"


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_spec_version_repo(db_session)
    assert repo.get_by_id(999_999_999) is None


def test_add_accepts_null_tasks_and_plan(db_session: Session, git_repo_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0002-null-sidecars", repo_id=git_repo_id)
    repo = create_spec_version_repo(db_session)
    row = repo.add(spec_id=spec.id, spec_md="# S", tasks_md=None, plan_md=None)

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.spec_md == "# S"
    assert loaded.tasks_md is None
    assert loaded.plan_md is None
