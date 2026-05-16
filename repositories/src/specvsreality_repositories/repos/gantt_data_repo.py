"""Read-only queries for gantt chart assembly (no timeline logic)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.implements import Implements
from specvsreality_repositories.models.requirement import Requirement
from specvsreality_repositories.models.requirement_version import RequirementVersion


class GanttDataRepo:
    """Plain selects for requirement / artifact / implements data used by the gantt facade."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_requirements_for_spec_ordered(self, *, spec_id: int) -> list[Requirement]:
        stmt = (
            select(Requirement)
            .where(Requirement.spec_id == spec_id)
            .order_by(Requirement.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_requirement_versions_ordered(self, *, requirement_id: int) -> list[RequirementVersion]:
        stmt = (
            select(RequirementVersion)
            .where(RequirementVersion.requirement_id == requirement_id)
            .order_by(RequirementVersion.commit_datetime.asc(), RequirementVersion.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_implements_with_artifact_versions(
        self,
        *,
        requirement_version_ids: Sequence[int],
    ) -> list[tuple[Implements, ArtifactVersion, Artifact]]:
        if not requirement_version_ids:
            return []
        stmt = (
            select(Implements, ArtifactVersion, Artifact)
            .join(ArtifactVersion, ArtifactVersion.id == Implements.artifact_version_id)
            .join(Artifact, Artifact.id == ArtifactVersion.artifact_id)
            .where(Implements.requirement_version_id.in_(requirement_version_ids))
        )
        rows = self._session.execute(stmt).all()
        return [(impl, av, art) for impl, av, art in rows]

    def list_artifact_versions_for_artifact_ids_ordered(
        self,
        *,
        artifact_ids: Sequence[int],
    ) -> list[ArtifactVersion]:
        if not artifact_ids:
            return []
        stmt = (
            select(ArtifactVersion)
            .where(ArtifactVersion.artifact_id.in_(artifact_ids))
            .order_by(
                ArtifactVersion.artifact_id.asc(),
                ArtifactVersion.commit_datetime.asc(),
                ArtifactVersion.id.asc(),
            )
        )
        return list(self._session.scalars(stmt).all())


def create_gantt_data_repo(session: Session) -> GanttDataRepo:
    return GanttDataRepo(session)
