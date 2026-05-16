"""Tests for `RequirementRepo`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_requirement_repo, create_spec_repo


def test_get_by_id_returns_row_after_add(db_session: Session, git_repo_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0001-req", repo_id=git_repo_id)
    repo = create_requirement_repo(db_session)
    row = repo.add(spec_id=spec.id, paper_id="FR-1")

    assert repo.get_by_id(row.id) == row


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_requirement_repo(db_session)
    assert repo.get_by_id(999_999_999) is None


def test_get_by_spec_and_paper_id_returns_matching_row(db_session: Session, git_repo_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0001-scope", repo_id=git_repo_id)
    repo = create_requirement_repo(db_session)
    row = repo.add(spec_id=spec.id, paper_id="FR-9")

    assert repo.get_by_spec_and_paper_id(spec_id=spec.id, paper_id="FR-9") == row


def test_get_by_spec_and_paper_id_returns_none_when_paper_id_differs(
    db_session: Session,
    git_repo_id: int,
) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0001-scope2", repo_id=git_repo_id)
    repo = create_requirement_repo(db_session)
    repo.add(spec_id=spec.id, paper_id="FR-1")

    assert repo.get_by_spec_and_paper_id(spec_id=spec.id, paper_id="FR-999") is None


def test_get_by_spec_and_paper_id_returns_none_when_spec_id_differs(
    db_session: Session,
    git_repo_id: int,
) -> None:
    spec_a = create_spec_repo(db_session).add(paper_id="0001-sa", repo_id=git_repo_id)
    spec_b = create_spec_repo(db_session).add(paper_id="0001-sb", repo_id=git_repo_id)
    repo = create_requirement_repo(db_session)
    repo.add(spec_id=spec_a.id, paper_id="SHARED")

    assert repo.get_by_spec_and_paper_id(spec_id=spec_b.id, paper_id="SHARED") is None
