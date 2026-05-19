"""Read-only queries for gantt chart assembly."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import asc, desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.commit_file import CommitFile
from specvsreality_repositories.models.implementation_claim import ImplementationClaim
from specvsreality_repositories.models.requirement import Requirement
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.models.spec_version import SpecVersion


class GanttDataRepo:
    """Plain selects supporting the gantt facade."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_requirements_for_spec_ordered(
        self, *, spec_id: int
    ) -> list[Requirement]:
        stmt = (
            select(Requirement)
            .where(Requirement.spec_id == spec_id)
            .order_by(Requirement.external_id.asc(), Requirement.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_versions_with_anchor_for_requirement(
        self, *, requirement_id: int
    ) -> list[tuple[RequirementVersion, SpecVersion]]:
        """Each ``(rv, spec_version)`` ordered by ``spec_version.first_seen_at``."""
        stmt = (
            select(RequirementVersion, SpecVersion)
            .join(SpecVersion, SpecVersion.id == RequirementVersion.spec_version_id)
            .where(RequirementVersion.requirement_id == requirement_id)
            .order_by(asc(SpecVersion.first_seen_at), asc(RequirementVersion.id))
        )
        return [(rv, sv) for rv, sv in self._session.execute(stmt).all()]

    def latest_claims_for_requirement_versions(
        self,
        *,
        requirement_version_ids: Sequence[int],
    ) -> list[ImplementationClaim]:
        """Most recent claim per ``(requirement_version, blob)`` pair."""
        if not requirement_version_ids:
            return []
        latest = (
            select(ImplementationClaim)
            .where(
                ImplementationClaim.requirement_version_id.in_(requirement_version_ids),
            )
            .order_by(
                ImplementationClaim.requirement_version_id.asc(),
                ImplementationClaim.blob_sha.asc(),
                desc(ImplementationClaim.evaluated_at),
                desc(ImplementationClaim.id),
            )
            .distinct(
                ImplementationClaim.requirement_version_id,
                ImplementationClaim.blob_sha,
            )
        )
        return list(self._session.scalars(latest).all())

    def list_paths_for_blobs_in_repo(
        self, *, repository_id: int, blob_shas: Sequence[str]
    ) -> dict[str, list[tuple[str, str]]]:
        """Return ``blob_sha -> [(commit_sha, path)]`` for blobs in the repo's history."""
        if not blob_shas:
            return {}
        stmt = (
            select(CommitFile.blob_sha, CommitFile.commit_sha, CommitFile.path)
            .join(Commit, Commit.sha == CommitFile.commit_sha)
            .where(
                Commit.repository_id == repository_id,
                CommitFile.blob_sha.in_(blob_shas),
            )
        )
        out: dict[str, list[tuple[str, str]]] = {}
        for blob_sha, commit_sha, path in self._session.execute(stmt).all():
            out.setdefault(blob_sha, []).append((commit_sha, path))
        return out


def create_gantt_data_repo(session: Session) -> GanttDataRepo:
    return GanttDataRepo(session)
