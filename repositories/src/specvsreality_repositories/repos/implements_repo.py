"""Repository access for requirement–artifact implementation links."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.models.implements import Implements


class ImplementsRepo:
    """Read/write access for implements association rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_requirement_version_and_artifact_version(
        self,
        *,
        requirement_version_id: int,
        artifact_version_id: int,
    ) -> Implements | None:
        """Return the link row between this requirement version and artifact version, if present."""
        return self._session.get(
            Implements,
            (requirement_version_id, artifact_version_id),
        )

    def get(
        self,
        *,
        requirement_version_id: int,
        artifact_version_id: int,
    ) -> Implements | None:
        return self.get_by_requirement_version_and_artifact_version(
            requirement_version_id=requirement_version_id,
            artifact_version_id=artifact_version_id,
        )

    def add(self, *, requirement_version_id: int, artifact_version_id: int) -> Implements:
        row = Implements(
            requirement_version_id=requirement_version_id,
            artifact_version_id=artifact_version_id,
        )
        self._session.add(row)
        self._session.flush()
        return row


def create_implements_repo(session: Session) -> ImplementsRepo:
    return ImplementsRepo(session)
