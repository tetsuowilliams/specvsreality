"""Repository access for requirement–artifact implementation links."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.implements import Implements


class ImplementsRepo:
    """Read/write access for implements association rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_implementation_and_artifact_version(
        self,
        *,
        implementation_at_commit_id: int,
        artifact_version_id: int,
    ) -> Implements | None:
        return self._session.get(
            Implements,
            (implementation_at_commit_id, artifact_version_id),
        )

    def get(
        self,
        *,
        implementation_at_commit_id: int,
        artifact_version_id: int,
    ) -> Implements | None:
        return self.get_by_implementation_and_artifact_version(
            implementation_at_commit_id=implementation_at_commit_id,
            artifact_version_id=artifact_version_id,
        )

    def get_for_implementation_and_filepath(
        self,
        *,
        implementation_at_commit_id: int,
        filepath: str,
    ) -> Implements | None:
        normalized = filepath.replace("\\", "/")
        stmt = (
            select(Implements)
            .join(ArtifactVersion, ArtifactVersion.id == Implements.artifact_version_id)
            .join(Artifact, Artifact.id == ArtifactVersion.artifact_id)
            .where(
                Implements.implementation_at_commit_id == implementation_at_commit_id,
                Artifact.filepath == normalized,
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def add(
        self,
        *,
        implementation_at_commit_id: int,
        artifact_version_id: int,
    ) -> Implements:
        row = Implements(
            implementation_at_commit_id=implementation_at_commit_id,
            artifact_version_id=artifact_version_id,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def update_evidence(
        self,
        *,
        implementation_at_commit_id: int,
        artifact_version_id: int,
        evidence_file: str,
        evidence_line_number: int | None,
        evidence_snippet: str,
        evidence_relevance: str,
    ) -> Implements | None:
        row = self.get(
            implementation_at_commit_id=implementation_at_commit_id,
            artifact_version_id=artifact_version_id,
        )
        if row is None:
            return None

        row.evidence_file = evidence_file
        row.evidence_line_number = evidence_line_number
        row.evidence_snippet = evidence_snippet
        row.evidence_relevance = evidence_relevance
        self._session.flush()
        return row

    def update_evidence_for_filepath(
        self,
        *,
        implementation_at_commit_id: int,
        filepath: str,
        evidence_file: str,
        evidence_line_number: int | None,
        evidence_snippet: str,
        evidence_relevance: str,
    ) -> Implements | None:
        row = self.get_for_implementation_and_filepath(
            implementation_at_commit_id=implementation_at_commit_id,
            filepath=filepath,
        )
        if row is None:
            return None

        row.evidence_file = evidence_file
        row.evidence_line_number = evidence_line_number
        row.evidence_snippet = evidence_snippet
        row.evidence_relevance = evidence_relevance
        self._session.flush()
        return row

    def upsert_evidence(
        self,
        *,
        implementation_at_commit_id: int,
        artifact_version_id: int,
        evidence_file: str,
        evidence_line_number: int | None,
        evidence_snippet: str,
        evidence_relevance: str,
    ) -> Implements:
        """Create or update the implementation–artifact link and attach evidence."""
        row = self.get(
            implementation_at_commit_id=implementation_at_commit_id,
            artifact_version_id=artifact_version_id,
        )
        if row is None:
            row = Implements(
                implementation_at_commit_id=implementation_at_commit_id,
                artifact_version_id=artifact_version_id,
            )
            self._session.add(row)

        row.evidence_file = evidence_file
        row.evidence_line_number = evidence_line_number
        row.evidence_snippet = evidence_snippet
        row.evidence_relevance = evidence_relevance
        self._session.flush()
        return row


def create_implements_repo(session: Session) -> ImplementsRepo:
    return ImplementsRepo(session)
