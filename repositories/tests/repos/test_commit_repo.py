"""Tests for ``CommitRepo``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import CommitRepo


def test_insert_then_exists_and_get(db_session: Session, repository_id: int) -> None:
    commits = CommitRepo(db_session)
    sha = "1" * 40
    ts = datetime.now(UTC)
    commits.insert(
        sha=sha,
        repository_id=repository_id,
        commit_date=ts,
        author_name="Ada",
        message="initial",
    )

    assert commits.exists(sha) is True
    row = commits.get(sha)
    assert row is not None
    assert row.author_name == "Ada"
    assert row.message == "initial"


def test_insert_parents_records_each_edge(db_session: Session, repository_id: int) -> None:
    commits = CommitRepo(db_session)
    ts = datetime.now(UTC)
    parent_a = "a" * 40
    parent_b = "b" * 40
    child = "c" * 40
    commits.insert(sha=parent_a, repository_id=repository_id, commit_date=ts)
    commits.insert(
        sha=parent_b,
        repository_id=repository_id,
        commit_date=ts + timedelta(seconds=1),
    )
    commits.insert(
        sha=child,
        repository_id=repository_id,
        commit_date=ts + timedelta(seconds=2),
    )

    commits.insert_parents(commit_sha=child, parents=[(parent_a, 0), (parent_b, 1)])


def test_insert_parents_empty_is_noop(db_session: Session, repository_id: int) -> None:
    commits = CommitRepo(db_session)
    sha = "9" * 40
    commits.insert(sha=sha, repository_id=repository_id, commit_date=datetime.now(UTC))
    commits.insert_parents(commit_sha=sha, parents=[])


def test_iter_for_repo_orders_oldest_first(
    db_session: Session, repository_id: int
) -> None:
    commits = CommitRepo(db_session)
    base = datetime.now(UTC)
    earlier = "e" * 40
    later = "f" * 40
    commits.insert(sha=later, repository_id=repository_id, commit_date=base + timedelta(days=1))
    commits.insert(sha=earlier, repository_id=repository_id, commit_date=base)

    shas_oldest_first = [
        c.sha
        for c in commits.iter_for_repo(repository_id=repository_id, oldest_first=True)
    ]
    assert shas_oldest_first.index(earlier) < shas_oldest_first.index(later)
