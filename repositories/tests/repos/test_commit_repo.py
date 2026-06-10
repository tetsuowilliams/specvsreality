"""Tests for `CommitRepo`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_commit_repo
from tests.fixtures.graph import add_commit, add_git_repo

_DT = datetime(2026, 1, 15, tzinfo=UTC)


def test_get_or_create_round_trips_via_get_by_id(db_session: Session, git_repo_id: int) -> None:
    repo = create_commit_repo(db_session)
    row = repo.get_or_create(
        repo_id=git_repo_id,
        commit_sha="b" * 40,
        commit_message="initial",
        committed_at=_DT,
    )

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.repo_id == git_repo_id
    assert loaded.commit_sha == "b" * 40
    assert loaded.commit_message == "initial"
    assert loaded.committed_at == _DT


def test_get_by_sha_returns_matching_commit(db_session: Session, git_repo_id: int) -> None:
    repo = create_commit_repo(db_session)
    row = repo.get_or_create(
        repo_id=git_repo_id,
        commit_sha="c" * 40,
        commit_message="find me",
        committed_at=_DT,
    )

    found = repo.get_by_sha(repo_id=git_repo_id, commit_sha="c" * 40)
    assert found is not None
    assert found.id == row.id


def test_get_by_sha_scoped_by_repo(db_session: Session) -> None:
    repo_a = add_git_repo(db_session, name="a", url="https://example.test/a.git")
    repo_b = add_git_repo(db_session, name="b", url="https://example.test/b.git")
    commit_repo = create_commit_repo(db_session)
    sha = "d" * 40
    commit_repo.get_or_create(
        repo_id=repo_a.id,
        commit_sha=sha,
        commit_message="only in a",
        committed_at=_DT,
    )

    assert commit_repo.get_by_sha(repo_id=repo_a.id, commit_sha=sha) is not None
    assert commit_repo.get_by_sha(repo_id=repo_b.id, commit_sha=sha) is None


def test_get_or_create_is_idempotent(db_session: Session, git_repo_id: int) -> None:
    repo = create_commit_repo(db_session)
    first = repo.get_or_create(
        repo_id=git_repo_id,
        commit_sha="e" * 40,
        commit_message="first",
        committed_at=_DT,
    )
    second = repo.get_or_create(
        repo_id=git_repo_id,
        commit_sha="e" * 40,
        commit_message="ignored",
        committed_at=_DT,
    )

    assert second.id == first.id
    assert second.commit_message == "first"


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_commit_repo(db_session)
    assert repo.get_by_id(999_999_999) is None


def test_get_by_sha_returns_none_for_unknown_sha(db_session: Session, git_repo_id: int) -> None:
    repo = create_commit_repo(db_session)
    add_commit(db_session, repo_id=git_repo_id, commit_sha="f" * 40)
    assert repo.get_by_sha(repo_id=git_repo_id, commit_sha="0" * 40) is None
