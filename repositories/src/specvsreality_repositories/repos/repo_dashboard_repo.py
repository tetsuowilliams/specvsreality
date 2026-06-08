"""Read-side queries for repository dashboard and sidebar."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_candidate import ArtifactCandidate
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.enums import SpecItemImportance
from specvsreality_repositories.models.git_repo import GitRepo
from specvsreality_repositories.models.implementation_at_commit import ImplementationAtCommit
from specvsreality_repositories.models.implements import Implements
from specvsreality_repositories.models.spec import Spec
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion

_TRACKED_IMPORTANCE = (
    SpecItemImportance.MUST,
    SpecItemImportance.SHOULD,
)
_LOW_CONFIDENCE_THRESHOLD = 0.7


@dataclass(frozen=True, slots=True)
class SpecLatestVersionRow:
    spec: Spec
    version: SpecVersion
    commit: Commit


@dataclass(frozen=True, slots=True)
class LatestEvaluationRow:
    implementation: ImplementationAtCommit
    commit: Commit
    spec_item: SpecItem
    spec: Spec
    version: SpecVersion


@dataclass(frozen=True, slots=True)
class ArtifactActivityRow:
    filepath: str
    link_type: str
    item_count: int
    spec_paper_id: str | None


class RepoDashboardRepo:
    """Repo-scoped dashboard reads."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_repo(self, repo_id: int) -> GitRepo | None:
        return self._session.get(GitRepo, repo_id)

    def get_cursor_commit(self, *, repo_id: int, cursor_sha: str) -> Commit | None:
        if not cursor_sha:
            return None
        stmt = select(Commit).where(
            Commit.repo_id == repo_id,
            Commit.commit_sha == cursor_sha,
        )
        return self._session.scalars(stmt).first()

    def get_latest_analysed_commit(self, *, repo_id: int) -> Commit | None:
        stmt = (
            select(Commit)
            .where(Commit.repo_id == repo_id)
            .order_by(desc(Commit.committed_at), desc(Commit.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def count_specs(self, *, repo_id: int) -> int:
        stmt = select(func.count()).select_from(Spec).where(Spec.repo_id == repo_id)
        return int(self._session.scalar(stmt) or 0)

    def list_all_spec_versions_for_repo(self, *, repo_id: int) -> list[SpecLatestVersionRow]:
        stmt = (
            select(Spec, SpecVersion, Commit)
            .join(SpecVersion, SpecVersion.spec_id == Spec.id)
            .join(Commit, Commit.id == SpecVersion.commit_id)
            .where(Spec.repo_id == repo_id)
            .order_by(
                Spec.paper_id.asc(),
                Spec.id.asc(),
                desc(Commit.committed_at),
                desc(SpecVersion.id),
            )
        )
        return [
            SpecLatestVersionRow(spec=spec, version=version, commit=commit)
            for spec, version, commit in self._session.execute(stmt).all()
        ]

    def list_specs_latest_versions(self, *, repo_id: int) -> list[SpecLatestVersionRow]:
        latest_version = (
            select(
                SpecVersion.spec_id.label("spec_id"),
                func.max(SpecVersion.id).label("version_id"),
            )
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .where(Spec.repo_id == repo_id)
            .group_by(SpecVersion.spec_id)
            .subquery()
        )
        stmt = (
            select(Spec, SpecVersion, Commit)
            .join(latest_version, latest_version.c.spec_id == Spec.id)
            .join(SpecVersion, SpecVersion.id == latest_version.c.version_id)
            .join(Commit, Commit.id == SpecVersion.commit_id)
            .where(Spec.repo_id == repo_id)
            .order_by(Spec.paper_id.asc(), Spec.id.asc())
        )
        return [
            SpecLatestVersionRow(spec=spec, version=version, commit=commit)
            for spec, version, commit in self._session.execute(stmt).all()
        ]

    def list_items_for_versions(self, *, version_ids: Sequence[int]) -> list[SpecItem]:
        if not version_ids:
            return []
        stmt = (
            select(SpecItem)
            .where(SpecItem.spec_version_id.in_(version_ids))
            .order_by(SpecItem.spec_version_id.asc(), SpecItem.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_latest_evaluations_for_repo(self, *, repo_id: int) -> list[LatestEvaluationRow]:
        ranked = (
            select(
                ImplementationAtCommit.id.label("implementation_id"),
                func.row_number()
                .over(
                    partition_by=ImplementationAtCommit.spec_item_id,
                    order_by=(desc(Commit.committed_at), desc(ImplementationAtCommit.id)),
                )
                .label("row_num"),
            )
            .join(SpecItem, SpecItem.id == ImplementationAtCommit.spec_item_id)
            .join(SpecVersion, SpecVersion.id == SpecItem.spec_version_id)
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .join(Commit, Commit.id == ImplementationAtCommit.commit_id)
            .where(Spec.repo_id == repo_id)
            .subquery()
        )
        stmt = (
            select(ImplementationAtCommit, Commit, SpecItem, Spec, SpecVersion)
            .join(ranked, ranked.c.implementation_id == ImplementationAtCommit.id)
            .join(Commit, Commit.id == ImplementationAtCommit.commit_id)
            .join(SpecItem, SpecItem.id == ImplementationAtCommit.spec_item_id)
            .join(SpecVersion, SpecVersion.id == SpecItem.spec_version_id)
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .where(ranked.c.row_num == 1)
            .order_by(Spec.paper_id.asc(), SpecItem.local_key.asc())
        )
        return [
            LatestEvaluationRow(
                implementation=implementation,
                commit=commit,
                spec_item=item,
                spec=spec,
                version=version,
            )
            for implementation, commit, item, spec, version in self._session.execute(stmt).all()
        ]

    def count_candidates_for_versions(self, *, version_ids: Sequence[int]) -> dict[int, int]:
        if not version_ids:
            return {}
        stmt = (
            select(
                ArtifactCandidate.spec_version_id,
                func.count(ArtifactCandidate.id),
            )
            .where(ArtifactCandidate.spec_version_id.in_(version_ids))
            .group_by(ArtifactCandidate.spec_version_id)
        )
        return {version_id: int(count) for version_id, count in self._session.execute(stmt).all()}

    def list_recent_evaluations(
        self,
        *,
        repo_id: int,
        limit: int = 30,
    ) -> list[LatestEvaluationRow]:
        stmt = (
            select(ImplementationAtCommit, Commit, SpecItem, Spec, SpecVersion)
            .join(Commit, Commit.id == ImplementationAtCommit.commit_id)
            .join(SpecItem, SpecItem.id == ImplementationAtCommit.spec_item_id)
            .join(SpecVersion, SpecVersion.id == SpecItem.spec_version_id)
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .where(Spec.repo_id == repo_id)
            .order_by(desc(Commit.committed_at), desc(ImplementationAtCommit.id))
            .limit(limit)
        )
        return [
            LatestEvaluationRow(
                implementation=implementation,
                commit=commit,
                spec_item=item,
                spec=spec,
                version=version,
            )
            for implementation, commit, item, spec, version in self._session.execute(stmt).all()
        ]

    def list_prior_evaluation(
        self,
        *,
        repo_id: int,
        spec_id: int,
        local_key: str,
        before_committed_at: datetime,
    ) -> LatestEvaluationRow | None:
        stmt = (
            select(ImplementationAtCommit, Commit, SpecItem, Spec, SpecVersion)
            .join(Commit, Commit.id == ImplementationAtCommit.commit_id)
            .join(SpecItem, SpecItem.id == ImplementationAtCommit.spec_item_id)
            .join(SpecVersion, SpecVersion.id == SpecItem.spec_version_id)
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .where(
                Spec.repo_id == repo_id,
                Spec.id == spec_id,
                SpecItem.local_key == local_key,
                Commit.committed_at < before_committed_at,
            )
            .order_by(desc(Commit.committed_at), desc(ImplementationAtCommit.id))
            .limit(1)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        implementation, commit, item, spec, version = row
        return LatestEvaluationRow(
            implementation=implementation,
            commit=commit,
            spec_item=item,
            spec=spec,
            version=version,
        )

    def list_artifact_activity(self, *, repo_id: int, limit: int = 12) -> list[ArtifactActivityRow]:
        evidence_stmt = (
            select(
                Artifact.filepath,
                func.count(func.distinct(SpecItem.id)).label("item_count"),
                func.max(Spec.paper_id).label("paper_id"),
            )
            .join(ArtifactVersion, ArtifactVersion.artifact_id == Artifact.id)
            .join(Implements, Implements.artifact_version_id == ArtifactVersion.id)
            .join(
                ImplementationAtCommit,
                ImplementationAtCommit.id == Implements.implementation_at_commit_id,
            )
            .join(SpecItem, SpecItem.id == ImplementationAtCommit.spec_item_id)
            .join(SpecVersion, SpecVersion.id == SpecItem.spec_version_id)
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .join(Commit, Commit.id == ArtifactVersion.commit_id)
            .where(Commit.repo_id == repo_id)
            .group_by(Artifact.filepath)
            .order_by(desc("item_count"), Artifact.filepath.asc())
            .limit(limit)
        )
        evidence_rows = [
            ArtifactActivityRow(
                filepath=filepath,
                link_type="evidence",
                item_count=int(item_count),
                spec_paper_id=paper_id,
            )
            for filepath, item_count, paper_id in self._session.execute(evidence_stmt).all()
        ]

        candidate_stmt = (
            select(
                Artifact.filepath,
                func.count(ArtifactCandidate.id).label("candidate_count"),
                func.max(Spec.paper_id).label("paper_id"),
            )
            .join(ArtifactVersion, ArtifactVersion.artifact_id == Artifact.id)
            .join(ArtifactCandidate, ArtifactCandidate.artifact_version_id == ArtifactVersion.id)
            .join(SpecVersion, SpecVersion.id == ArtifactCandidate.spec_version_id)
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .join(Commit, Commit.id == ArtifactVersion.commit_id)
            .where(Commit.repo_id == repo_id)
            .group_by(Artifact.filepath)
            .order_by(desc("candidate_count"), Artifact.filepath.asc())
            .limit(limit)
        )
        candidate_rows = [
            ArtifactActivityRow(
                filepath=filepath,
                link_type="candidate",
                item_count=int(candidate_count),
                spec_paper_id=paper_id,
            )
            for filepath, candidate_count, paper_id in self._session.execute(candidate_stmt).all()
        ]
        return evidence_rows + candidate_rows

    @staticmethod
    def is_tracked_importance(importance: SpecItemImportance) -> bool:
        return importance in _TRACKED_IMPORTANCE

    @staticmethod
    def is_low_confidence(confidence: float | None) -> bool:
        return confidence is not None and confidence < _LOW_CONFIDENCE_THRESHOLD


def create_repo_dashboard_repo(session: Session) -> RepoDashboardRepo:
    return RepoDashboardRepo(session)
