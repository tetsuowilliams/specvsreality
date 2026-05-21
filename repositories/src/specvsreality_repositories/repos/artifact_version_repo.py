"""Repository access for artifact versions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion


class ArtifactVersionRepo:
    """Read/write access for artifact_version rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, version_id: int) -> ArtifactVersion | None:
        return self._session.get(ArtifactVersion, version_id)

    def get_latest_for_artifact_filepath(self, *, filepath: str) -> ArtifactVersion | None:
        """Newest ``ArtifactVersion`` for the artifact with this ``filepath`` (by commit time, then row id)."""
        normalized = filepath.replace("\\", "/")
        av = ArtifactVersion
        stmt = (
            select(av)
            .join(Artifact, Artifact.id == av.artifact_id)
            .where(Artifact.filepath == normalized)
            .order_by(desc(av.commit_datetime), desc(av.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_by_filepath_and_commit(self, *, filepath: str, commit_sha: str) -> ArtifactVersion | None:
        """``ArtifactVersion`` for this normalized ``filepath`` at ``commit_sha`` (newest row id if duplicates)."""
        normalized = filepath.replace("\\", "/")
        av = ArtifactVersion
        stmt = (
            select(av)
            .join(Artifact, Artifact.id == av.artifact_id)
            .where(Artifact.filepath == normalized, av.commit_sha == commit_sha)
            .order_by(desc(av.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def add(
        self,
        *,
        artifact_id: int,
        commit_sha: str,
        commit_datetime: datetime,
        status: str,
        file_content: str,
    ) -> ArtifactVersion:
        row = ArtifactVersion(
            artifact_id=artifact_id,
            commit_sha=commit_sha,
            commit_datetime=commit_datetime,
            status=status,
            file_content=file_content,
        )
        self._session.add(row)
        self._session.flush()
        return row


def create_artifact_version_repo(session: Session) -> ArtifactVersionRepo:
    return ArtifactVersionRepo(session)
