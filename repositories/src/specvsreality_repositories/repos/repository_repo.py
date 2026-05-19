"""Repository row access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.repository import Repository


class RepositoryRepo:
    """Read/write access for the ``repositories`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, repository_id: int) -> Repository | None:
        return self._session.get(Repository, repository_id)

    def get_by_name(self, name: str) -> Repository | None:
        stmt = select(Repository).where(Repository.name == name).limit(1)
        return self._session.scalars(stmt).first()

    def get_or_create(
        self,
        *,
        name: str,
        url: str,
        default_branch: str = "main",
    ) -> Repository:
        existing = self.get_by_name(name)
        if existing is not None:
            return existing
        row = Repository(name=name, url=url, default_branch=default_branch)
        self._session.add(row)
        self._session.flush()
        return row

    def add(
        self,
        *,
        name: str,
        url: str,
        default_branch: str = "main",
        clone_location: str | None = None,
        cursor_position: str | None = None,
    ) -> Repository:
        row = Repository(
            name=name,
            url=url,
            default_branch=default_branch,
            clone_location=clone_location,
            cursor_position=cursor_position,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_all(self) -> list[Repository]:
        stmt = select(Repository).order_by(Repository.name.asc(), Repository.id.asc())
        return list(self._session.scalars(stmt).all())


def create_repository_repo(session: Session) -> RepositoryRepo:
    return RepositoryRepo(session)
