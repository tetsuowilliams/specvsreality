"""Read-only joins for assembling the spec tree view."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.implementation_at_commit import ImplementationAtCommit
from specvsreality_repositories.models.implements import Implements
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion


class SpecTreeRepo:
    """Assembles the read-side joins for the spec -> versions -> items -> impl tree."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_versions_with_commit(self, *, spec_id: int) -> list[tuple[SpecVersion, Commit]]:
        stmt = (
            select(SpecVersion, Commit)
            .join(Commit, Commit.id == SpecVersion.commit_id)
            .where(SpecVersion.spec_id == spec_id)
            .order_by(Commit.committed_at.asc(), SpecVersion.id.asc())
        )
        return [tuple(row) for row in self._session.execute(stmt).all()]

    def get_latest_version_with_commit(self, *, spec_id: int) -> tuple[SpecVersion, Commit] | None:
        stmt = (
            select(SpecVersion, Commit)
            .join(Commit, Commit.id == SpecVersion.commit_id)
            .where(SpecVersion.spec_id == spec_id)
            .order_by(Commit.committed_at.desc(), SpecVersion.id.desc())
            .limit(1)
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        return tuple(row)

    def get_version_with_commit_at_commit(
        self,
        *,
        spec_id: int,
        commit_id: int,
    ) -> tuple[SpecVersion, Commit] | None:
        stmt = (
            select(SpecVersion, Commit)
            .join(Commit, Commit.id == SpecVersion.commit_id)
            .where(
                SpecVersion.spec_id == spec_id,
                SpecVersion.commit_id == commit_id,
            )
        )
        row = self._session.execute(stmt).first()
        if row is None:
            return None
        return tuple(row)

    def list_items_for_versions(self, *, spec_version_ids: Sequence[int]) -> list[SpecItem]:
        if not spec_version_ids:
            return []
        stmt = (
            select(SpecItem)
            .where(SpecItem.spec_version_id.in_(spec_version_ids))
            .order_by(SpecItem.spec_version_id.asc(), SpecItem.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_implementations_with_commit(
        self,
        *,
        spec_item_ids: Sequence[int],
        commit_id: int | None = None,
    ) -> list[tuple[ImplementationAtCommit, Commit]]:
        if not spec_item_ids:
            return []
        stmt = (
            select(ImplementationAtCommit, Commit)
            .join(Commit, Commit.id == ImplementationAtCommit.commit_id)
            .where(ImplementationAtCommit.spec_item_id.in_(spec_item_ids))
        )
        if commit_id is not None:
            stmt = stmt.where(ImplementationAtCommit.commit_id == commit_id)
        stmt = stmt.order_by(
            ImplementationAtCommit.spec_item_id.asc(),
            Commit.committed_at.asc(),
            ImplementationAtCommit.id.asc(),
        )
        return [tuple(row) for row in self._session.execute(stmt).all()]

    def list_implements_with_artifacts(
        self,
        *,
        implementation_at_commit_ids: Sequence[int],
    ) -> list[tuple[Implements, ArtifactVersion, Artifact]]:
        if not implementation_at_commit_ids:
            return []
        stmt = (
            select(Implements, ArtifactVersion, Artifact)
            .join(ArtifactVersion, ArtifactVersion.id == Implements.artifact_version_id)
            .join(Artifact, Artifact.id == ArtifactVersion.artifact_id)
            .where(Implements.implementation_at_commit_id.in_(implementation_at_commit_ids))
            .order_by(Implements.implementation_at_commit_id.asc(), Artifact.filepath.asc())
        )
        return [tuple(row) for row in self._session.execute(stmt).all()]


def create_spec_tree_repo(session: Session) -> SpecTreeRepo:
    return SpecTreeRepo(session)
