"""Repository access for artifact candidates."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact_candidate import ArtifactCandidate


class ArtifactCandidateRepo:
    """Read/write access for ``artifact_candidate`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, candidate_id: int) -> ArtifactCandidate | None:
        return self._session.get(ArtifactCandidate, candidate_id)

    def list_for_spec_version(self, *, spec_version_id: int) -> list[ArtifactCandidate]:
        stmt = (
            select(ArtifactCandidate)
            .where(ArtifactCandidate.spec_version_id == spec_version_id)
            .order_by(ArtifactCandidate.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def add(
        self,
        *,
        spec_version_id: int,
        artifact_version_id: int,
        reasoning: str,
    ) -> ArtifactCandidate:
        row = ArtifactCandidate(
            spec_version_id=spec_version_id,
            artifact_version_id=artifact_version_id,
            reasoning=reasoning,
        )
        self._session.add(row)
        self._session.flush()
        return row


def create_artifact_candidate_repo(session: Session) -> ArtifactCandidateRepo:
    return ArtifactCandidateRepo(session)
