"""Assemble commit decision log responses."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.schemas.repo_logs import (
    CommitLogEntry,
    CommitLogSidebarEntry,
    RepoCommitLogsResponse,
    RepoLogsSidebarResponse,
)
from specvsreality_repositories.repos import (
    create_commit_log_repo,
    create_commit_repo,
    create_git_repo_repo,
)


class RepoLogsFacade:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._git_repo_repo = create_git_repo_repo(session)
        self._commit_repo = create_commit_repo(session)
        self._commit_log_repo = create_commit_log_repo(session)

    def get_sidebar(self, *, repo_id: int) -> RepoLogsSidebarResponse:
        if self._git_repo_repo.get_by_id(repo_id) is None:
            raise HTTPException(status_code=404, detail="repo not found")

        rows = self._commit_log_repo.list_sidebar_for_repo(repo_id=repo_id)
        return RepoLogsSidebarResponse(
            commits=[
                CommitLogSidebarEntry(
                    commit_sha=row.commit_sha,
                    commit_message=row.commit_message,
                    committed_at=row.committed_at,
                    log_count=row.log_count,
                )
                for row in rows
            ],
        )

    def get_commit_logs(
        self,
        *,
        repo_id: int,
        commit_sha: str,
    ) -> RepoCommitLogsResponse:
        if self._git_repo_repo.get_by_id(repo_id) is None:
            raise HTTPException(status_code=404, detail="repo not found")

        commit = self._commit_repo.get_by_sha(repo_id=repo_id, commit_sha=commit_sha)
        if commit is None:
            raise HTTPException(status_code=404, detail="commit not found")

        logs = self._commit_log_repo.list_for_commit(commit_id=commit.id)
        return RepoCommitLogsResponse(
            commit_sha=commit.commit_sha,
            commit_message=commit.commit_message,
            committed_at=commit.committed_at,
            logs=[
                CommitLogEntry(
                    action=log.action,
                    spec_folder=log.spec_folder,
                    message=log.message,
                    reasoning=log.reasoning,
                    created_at=log.created_at,
                )
                for log in logs
            ],
        )
