"""Queries for selecting which specs to scan during commit walk."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Float, and_, desc, func, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.enums import SpecItemImportance
from specvsreality_repositories.models.implementation_at_commit import ImplementationAtCommit
from specvsreality_repositories.models.implements import Implements
from specvsreality_repositories.models.spec import Spec
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion

_TRACKED = (SpecItemImportance.MUST.value, SpecItemImportance.SHOULD.value)


@dataclass(frozen=True, slots=True)
class UnderImplementedSpecRow:
    paper_id: str
    tracked: int
    implemented: int
    coverage: float | None


@dataclass(frozen=True, slots=True)
class ImplementationLinkedSpecRow:
    paper_id: str
    filepaths: tuple[str, ...]


class ScanSelectionRepo:
    """Repo-scoped queries for commit-walk scan selection."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_under_implemented_specs_at_commit(
        self,
        *,
        repo_id: int,
        commit_id: int,
        coverage_threshold: float = 0.7,
    ) -> list[UnderImplementedSpecRow]:
        """Specs whose tracked-item coverage at commit is below ``coverage_threshold``."""
        target = self._session.get(Commit, commit_id)
        if target is None:
            return []

        as_of = target.committed_at

        latest_version = (
            select(
                SpecVersion.spec_id.label("spec_id"),
                SpecVersion.id.label("version_id"),
                func.row_number()
                .over(
                    partition_by=SpecVersion.spec_id,
                    order_by=(desc(Commit.committed_at), desc(SpecVersion.id)),
                )
                .label("row_num"),
            )
            .join(Commit, Commit.id == SpecVersion.commit_id)
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .where(Spec.repo_id == repo_id, Commit.committed_at <= as_of)
            .subquery()
        )

        latest_eval = (
            select(
                ImplementationAtCommit.spec_item_id.label("spec_item_id"),
                ImplementationAtCommit.implemented.label("implemented"),
                func.row_number()
                .over(
                    partition_by=ImplementationAtCommit.spec_item_id,
                    order_by=(desc(Commit.committed_at), desc(ImplementationAtCommit.id)),
                )
                .label("row_num"),
            )
            .join(Commit, Commit.id == ImplementationAtCommit.commit_id)
            .where(Commit.committed_at <= as_of)
            .subquery()
        )

        tracked_expr = SpecItem.importance.in_(_TRACKED)
        implemented_expr = and_(
            latest_eval.c.row_num == 1,
            latest_eval.c.implemented.is_(True),
        )

        stmt = (
            select(
                Spec.paper_id,
                func.count(SpecItem.id).filter(tracked_expr).label("tracked"),
                func.count(SpecItem.id).filter(and_(tracked_expr, implemented_expr)).label(
                    "implemented"
                ),
            )
            .join(latest_version, and_(latest_version.c.spec_id == Spec.id, latest_version.c.row_num == 1))
            .join(SpecVersion, SpecVersion.id == latest_version.c.version_id)
            .join(SpecItem, SpecItem.spec_version_id == SpecVersion.id)
            .outerjoin(
                latest_eval,
                and_(
                    latest_eval.c.spec_item_id == SpecItem.id,
                    latest_eval.c.row_num == 1,
                ),
            )
            .where(Spec.repo_id == repo_id)
            .group_by(Spec.id, Spec.paper_id)
            .having(
                and_(
                    func.count(SpecItem.id).filter(tracked_expr) > 0,
                    (
                        func.count(SpecItem.id)
                        .filter(and_(tracked_expr, implemented_expr))
                        .cast(Float)
                        / func.count(SpecItem.id).filter(tracked_expr).cast(Float)
                    )
                    < coverage_threshold,
                )
            )
            .order_by(Spec.paper_id.asc())
        )

        rows: list[UnderImplementedSpecRow] = []
        for paper_id, tracked, implemented in self._session.execute(stmt).all():
            tracked_i = int(tracked)
            implemented_i = int(implemented)
            coverage = round((implemented_i / tracked_i) * 100, 1) if tracked_i else None
            rows.append(
                UnderImplementedSpecRow(
                    paper_id=paper_id,
                    tracked=tracked_i,
                    implemented=implemented_i,
                    coverage=coverage,
                )
            )
        return rows

    def list_specs_for_changed_artifacts_at_commit(
        self,
        *,
        commit_id: int,
    ) -> list[ImplementationLinkedSpecRow]:
        """Specs linked via implements to code artifacts changed at ``commit_id``.

        Matches specs whose implements evidence points at any version of an artifact
        that received a new ``artifact_version`` row at ``commit_id``. Historic
        evaluations typically still reference older artifact versions, so we join
        on ``artifact_id`` rather than requiring the link to target this commit.
        """
        changed_artifacts = (
            select(
                ArtifactVersion.artifact_id.label("artifact_id"),
                Artifact.filepath.label("filepath"),
            )
            .join(Artifact, Artifact.id == ArtifactVersion.artifact_id)
            .where(ArtifactVersion.commit_id == commit_id)
            .subquery()
        )
        stmt = (
            select(Spec.paper_id, changed_artifacts.c.filepath)
            .select_from(changed_artifacts)
            .join(
                ArtifactVersion,
                ArtifactVersion.artifact_id == changed_artifacts.c.artifact_id,
            )
            .join(Implements, Implements.artifact_version_id == ArtifactVersion.id)
            .join(
                ImplementationAtCommit,
                ImplementationAtCommit.id == Implements.implementation_at_commit_id,
            )
            .join(SpecItem, SpecItem.id == ImplementationAtCommit.spec_item_id)
            .join(SpecVersion, SpecVersion.id == SpecItem.spec_version_id)
            .join(Spec, Spec.id == SpecVersion.spec_id)
            .distinct()
            .order_by(Spec.paper_id.asc(), changed_artifacts.c.filepath.asc())
        )

        by_paper: dict[str, list[str]] = {}
        for paper_id, filepath in self._session.execute(stmt).all():
            by_paper.setdefault(paper_id, []).append(filepath)

        return [
            ImplementationLinkedSpecRow(paper_id=paper_id, filepaths=tuple(paths))
            for paper_id, paths in sorted(by_paper.items())
        ]


def create_scan_selection_repo(session: Session) -> ScanSelectionRepo:
    return ScanSelectionRepo(session)
