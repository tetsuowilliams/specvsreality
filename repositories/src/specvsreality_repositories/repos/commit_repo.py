"""Commit row access."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from datetime import datetime

from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.commit_parent import CommitParent


class CommitRepo:
    """Read/write access for ``commits`` and ``commit_parents``."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, sha: str) -> bool:
        stmt = select(Commit.sha).where(Commit.sha == sha).limit(1)
        return self._session.scalars(stmt).first() is not None

    def get(self, sha: str) -> Commit | None:
        return self._session.get(Commit, sha)

    def insert(
        self,
        *,
        sha: str,
        repository_id: int,
        commit_date: datetime,
        author_name: str | None = None,
        author_email: str | None = None,
        author_date: datetime | None = None,
        committer_name: str | None = None,
        committer_email: str | None = None,
        message: str | None = None,
    ) -> Commit:
        row = Commit(
            sha=sha,
            repository_id=repository_id,
            author_name=author_name,
            author_email=author_email,
            author_date=author_date,
            committer_name=committer_name,
            committer_email=committer_email,
            commit_date=commit_date,
            message=message,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def insert_parents(
        self, *, commit_sha: str, parents: Iterable[tuple[str, int]]
    ) -> None:
        """``parents`` is an iterable of ``(parent_sha, parent_order)`` tuples."""
        rows = [
            CommitParent(
                commit_sha=commit_sha,
                parent_sha=parent_sha,
                parent_order=parent_order,
            )
            for parent_sha, parent_order in parents
        ]
        if not rows:
            return
        self._session.add_all(rows)
        self._session.flush()

    def iter_for_repo(
        self, *, repository_id: int, oldest_first: bool = True
    ) -> Iterator[Commit]:
        order_col = (
            asc(Commit.commit_date) if oldest_first else desc(Commit.commit_date)
        )
        stmt = (
            select(Commit)
            .where(Commit.repository_id == repository_id)
            .order_by(order_col, Commit.sha.asc())
        )
        yield from self._session.scalars(stmt)


def create_commit_repo(session: Session) -> CommitRepo:
    return CommitRepo(session)
