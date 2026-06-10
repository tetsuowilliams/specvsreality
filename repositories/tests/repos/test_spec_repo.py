"""Tests for `SpecRepo`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_spec_repo


def test_get_by_paper_id_returns_row_for_repo(db_session: Session, git_repo_id: int) -> None:
    paper_a = "0001-feature-a"
    paper_b = "0002-feature-b"
    repo = create_spec_repo(db_session)
    row_a = repo.add(paper_id=paper_a, repo_id=git_repo_id)
    row_b = repo.add(paper_id=paper_b, repo_id=git_repo_id)

    assert repo.get_by_paper_id(paper_id=paper_a, repo_id=git_repo_id).id == row_a.id
    assert repo.get_by_paper_id(paper_id=paper_b, repo_id=git_repo_id).id == row_b.id


def test_get_by_paper_id_scoped_by_repo(db_session: Session, git_repo_id: int) -> None:
    paper_id = "0001-feature-a"
    other_repo = 0
    repo = create_spec_repo(db_session)
    row = repo.add(paper_id=paper_id, repo_id=git_repo_id)

    assert repo.get_by_paper_id(paper_id=paper_id, repo_id=git_repo_id) == row
    assert repo.get_by_paper_id(paper_id=paper_id, repo_id=other_repo) is None


def test_get_by_id_returns_row_after_add(db_session: Session, git_repo_id: int) -> None:
    repo = create_spec_repo(db_session)
    row = repo.add(paper_id="0001-x", repo_id=git_repo_id)

    assert repo.get_by_id(row.id) == row


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_spec_repo(db_session)
    assert repo.get_by_id(999_999_999) is None


def test_get_or_create_for_folder_upserts_by_normalized_path(
    db_session: Session,
    git_repo_id: int,
) -> None:
    repo = create_spec_repo(db_session)
    first, created = repo.get_or_create_for_folder(folder="specs/feature-a", repo_id=git_repo_id)
    assert created is True
    assert first.paper_id == "specs/feature-a"

    second, created = repo.get_or_create_for_folder(
        folder="specs/feature-a/",
        repo_id=git_repo_id,
    )
    assert created is False
    assert second.id == first.id


def test_list_for_repo_orders_by_paper_id(db_session: Session, git_repo_id: int) -> None:
    repo = create_spec_repo(db_session)
    s_b = repo.add(paper_id="b-paper", repo_id=git_repo_id)
    s_a = repo.add(paper_id="a-paper", repo_id=git_repo_id)

    rows = repo.list_for_repo(repo_id=git_repo_id)
    assert [r.id for r in rows] == [s_a.id, s_b.id]


def test_get_or_create_for_folder_reuses_legacy_basename_row(
    db_session: Session,
    git_repo_id: int,
) -> None:
    repo = create_spec_repo(db_session)
    legacy = repo.add(paper_id="feature-a", repo_id=git_repo_id)

    resolved, created = repo.get_or_create_for_folder(
        folder="specs/feature-a",
        repo_id=git_repo_id,
    )

    assert created is False
    assert resolved.id == legacy.id
    assert resolved.paper_id == "specs/feature-a"
