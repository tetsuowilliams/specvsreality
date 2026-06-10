"""Repository access for commit decision logs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.commit_log import CommitLog


@dataclass(frozen=True, slots=True)
class CommitLogSidebarRow:
    commit_id: int
    commit_sha: str
    commit_message: str
    committed_at: datetime
    log_count: int


class CommitLogRepo:
    """Read/write access for ``commit_log`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def append(
        self,
        *,
        commit_id: int,
        action: str,
        spec_folder: str,
        message: str,
        reasoning: str,
    ) -> CommitLog:
        row = CommitLog(
            commit_id=commit_id,
            action=action,
            spec_folder=spec_folder,
            message=message,
            reasoning=reasoning,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_commit(self, *, commit_id: int) -> list[CommitLog]:
        stmt = (
            select(CommitLog)
            .where(CommitLog.commit_id == commit_id)
            .order_by(CommitLog.created_at.asc(), CommitLog.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_sidebar_for_repo(self, *, repo_id: int) -> list[CommitLogSidebarRow]:
        stmt = (
            select(
                Commit.id,
                Commit.commit_sha,
                Commit.commit_message,
                Commit.committed_at,
                func.count(CommitLog.id),
            )
            .join(CommitLog, CommitLog.commit_id == Commit.id)
            .where(Commit.repo_id == repo_id)
            .group_by(Commit.id, Commit.commit_sha, Commit.commit_message, Commit.committed_at)
            .order_by(desc(Commit.committed_at), desc(Commit.id))
        )
        return [
            CommitLogSidebarRow(
                commit_id=commit_id,
                commit_sha=commit_sha,
                commit_message=commit_message,
                committed_at=committed_at,
                log_count=int(log_count),
            )
            for commit_id, commit_sha, commit_message, committed_at, log_count in (
                self._session.execute(stmt).all()
            )
        ]


def create_commit_log_repo(session: Session) -> CommitLogRepo:
    return CommitLogRepo(session)
