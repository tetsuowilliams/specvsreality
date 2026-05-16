"""Repository access for artifacts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact


class ArtifactRepo:
    """Read/write access for artifact rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, artifact_id: int) -> Artifact | None:
        return self._session.get(Artifact, artifact_id)

    def add(self, *, filepath: str) -> Artifact:
        row = Artifact(filepath=filepath)
        self._session.add(row)
        self._session.flush()
        return row

    def get_by_filepath(self, filepath: str) -> Artifact | None:
        return self._session.query(Artifact).filter(Artifact.filepath == filepath).first()


def create_artifact_repo(session: Session) -> ArtifactRepo:
    return ArtifactRepo(session)
