"""Repository access for tracked git repositories."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.models.git_repo import GitRepo


class GitRepoRepo:
    """Read/write access for git repository rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, repo_id: int) -> GitRepo | None:
        return self._session.get(GitRepo, repo_id)

    def add(
        self,
        *,
        name: str,
        url: str,
        cursor_position: str = "",
        location: str = "",
        clone_error: str = "",
    ) -> GitRepo:
        row = GitRepo(
            name=name,
            url=url,
            cursor_position=cursor_position,
            location=location,
            clone_error=clone_error,
        )
        self._session.add(row)
        self._session.flush()
        return row


def create_git_repo_repo(session: Session) -> GitRepoRepo:
    return GitRepoRepo(session)

