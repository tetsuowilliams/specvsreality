"""Repository access for artifact versions."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.commit import Commit


class ArtifactVersionRepo:
    """Read/write access for artifact_version rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, version_id: int) -> ArtifactVersion | None:
        return self._session.get(ArtifactVersion, version_id)

    def get_latest_for_artifact_filepath(self, *, filepath: str) -> ArtifactVersion | None:
        """Newest ``ArtifactVersion`` for this ``filepath`` (by commit time, then row id)."""
        normalized = filepath.replace("\\", "/")
        av = ArtifactVersion
        stmt = (
            select(av)
            .join(Artifact, Artifact.id == av.artifact_id)
            .join(Commit, Commit.id == av.commit_id)
            .where(Artifact.filepath == normalized)
            .order_by(desc(Commit.committed_at), desc(av.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_by_filepath_and_commit(
        self, *, filepath: str, commit_id: int
    ) -> ArtifactVersion | None:
        """``ArtifactVersion`` for this ``filepath`` at ``commit_id`` (newest row id wins)."""
        normalized = filepath.replace("\\", "/")
        av = ArtifactVersion
        stmt = (
            select(av)
            .join(Artifact, Artifact.id == av.artifact_id)
            .where(Artifact.filepath == normalized, av.commit_id == commit_id)
            .order_by(desc(av.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_latest_for_artifact_filepath_at_or_before_commit(
        self,
        *,
        filepath: str,
        commit_id: int,
    ) -> ArtifactVersion | None:
        """Newest artifact snapshot for ``filepath`` at or before ``commit_id``."""
        target = self._session.get(Commit, commit_id)
        if target is None:
            return None
        normalized = filepath.replace("\\", "/")
        av = ArtifactVersion
        stmt = (
            select(av)
            .join(Artifact, Artifact.id == av.artifact_id)
            .join(Commit, Commit.id == av.commit_id)
            .where(
                Artifact.filepath == normalized,
                Commit.committed_at <= target.committed_at,
            )
            .order_by(desc(Commit.committed_at), desc(av.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def add(
        self,
        *,
        artifact_id: int,
        commit_id: int,
        status: str,
        file_content: str,
    ) -> ArtifactVersion:
        row = ArtifactVersion(
            artifact_id=artifact_id,
            commit_id=commit_id,
            status=status,
            file_content=file_content,
        )
        self._session.add(row)
        self._session.flush()
        return row


def create_artifact_version_repo(session: Session) -> ArtifactVersionRepo:
    return ArtifactVersionRepo(session)
