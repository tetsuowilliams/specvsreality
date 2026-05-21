"""Repository access for requirement versions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.implements import Implements
from specvsreality_repositories.models.requirement import Requirement
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.repos.enums import VersionStatus


class RequirementVersionRepo:
    """Read/write access for requirement_version rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, version_id: int) -> RequirementVersion | None:
        return self._session.get(RequirementVersion, version_id)

    def get_latest_for_requirement(self, *, requirement_id: int) -> RequirementVersion | None:
        """Most recent version row for ``requirement_id`` (by commit time, then row id)."""
        stmt = (
            select(RequirementVersion)
            .where(RequirementVersion.requirement_id == requirement_id)
            .order_by(desc(RequirementVersion.commit_datetime), desc(RequirementVersion.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_versions_at_commit(self, *, commit_sha: str) -> list[RequirementVersion]:
        """All version rows for ``commit_sha``."""
        stmt = (
            select(RequirementVersion)
            .where(RequirementVersion.commit_sha == commit_sha)
            .where(RequirementVersion.status.in_([VersionStatus.ACTIVE.value, VersionStatus.UPDATED.value]))
        )
        return list(self._session.scalars(stmt).all())

    def list_latest(self, *, spec_id: int | None = None) -> list[RequirementVersion]:
        """Latest version row for each requirement (optionally scoped to ``spec_id``)."""
        rv = RequirementVersion

        ranked_source = (
            select(
                rv.id,
                func.row_number()
                .over(
                    partition_by=rv.requirement_id,
                    order_by=(desc(rv.commit_datetime), desc(rv.id)),
                )
                .label("rn"),
            )
            .join(Requirement, Requirement.id == rv.requirement_id)
        )

        if spec_id is not None:
            ranked_source = ranked_source.where(Requirement.spec_id == spec_id)

        ranked = ranked_source.subquery()

        stmt = (
            select(rv)
            .join(ranked, rv.id == ranked.c.id)
            .where(ranked.c.rn == 1)
            .order_by(rv.requirement_id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def get_for_artifact_filepath(
        self,
        *,
        filepath: str,
        spec_id: int | None = None,
    ) -> list[RequirementVersion]:
        """
        Requirement versions linked to this path via ``implements`` → ``artifact_version`` → ``artifact``.

        ``filepath`` is compared to ``artifact.filepath`` (``\\`` normalized to ``/``). When ``spec_id`` is
        set, only versions whose parent requirement belongs to that spec are included. Duplicate rows from
        multiple links are collapsed to one ``RequirementVersion`` each.
        """
        normalized = filepath.replace("\\", "/")
        rv = RequirementVersion

        stmt = (
            select(rv)
            .join(Implements, Implements.requirement_version_id == rv.id)
            .join(ArtifactVersion, ArtifactVersion.id == Implements.artifact_version_id)
            .join(Artifact, Artifact.id == ArtifactVersion.artifact_id)
            .where(Artifact.filepath == normalized)
        )

        if spec_id is not None:
            stmt = stmt.join(Requirement, Requirement.id == rv.requirement_id).where(Requirement.spec_id == spec_id)
        
        stmt = stmt.order_by(rv.requirement_id.asc(), desc(rv.commit_datetime), desc(rv.id))
        return list(self._session.scalars(stmt).unique().all())

    def add(
        self,
        *,
        requirement_id: int,
        commit_sha: str,
        commit_datetime: datetime,
        requirement_text: str,
        filepath_globs: list[str],
        status: str,
    ) -> RequirementVersion:
        row = RequirementVersion(
            requirement_id=requirement_id,
            commit_sha=commit_sha,
            commit_datetime=commit_datetime,
            requirement_text=requirement_text,
            filepath_globs=filepath_globs,
            status=status,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def update_evaluation(
        self,
        *,
        requirement_version_id: int,
        implemented: bool,
        summary: str,
        gaps: list[str],
    ) -> RequirementVersion | None:
        row = self.get_by_id(requirement_version_id)
        if row is None:
            return None

        row.implemented = implemented
        row.summary = summary
        row.gaps = gaps
        self._session.flush()
        return row


def create_requirement_version_repo(session: Session) -> RequirementVersionRepo:
    return RequirementVersionRepo(session)
