"""Repository access for git commits."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.commit import Commit


class CommitRepo:
    """Read/write access for ``commit`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, commit_id: int) -> Commit | None:
        return self._session.get(Commit, commit_id)

    def get_by_sha(self, *, repo_id: int, commit_sha: str) -> Commit | None:
        stmt = select(Commit).where(
            Commit.repo_id == repo_id,
            Commit.commit_sha == commit_sha,
        )
        return self._session.scalars(stmt).first()

    def get_or_create(
        self,
        *,
        repo_id: int,
        commit_sha: str,
        commit_message: str,
        committed_at: datetime,
    ) -> Commit:
        existing = self.get_by_sha(repo_id=repo_id, commit_sha=commit_sha)
        if existing is not None:
            return existing
        row = Commit(
            repo_id=repo_id,
            commit_sha=commit_sha,
            commit_message=commit_message,
            committed_at=committed_at,
        )
        self._session.add(row)
        self._session.flush()
        return row


def create_commit_repo(session: Session) -> CommitRepo:
    return CommitRepo(session)
