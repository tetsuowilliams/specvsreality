"""Assemble compact sidebar response."""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from specvsreality_api.schemas.repo_sidebar import (
    RepoSidebarResponse,
    SidebarSpec,
    SidebarSpecVersion,
)
from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.enums import SpecItemImportance
from specvsreality_repositories.models.implementation_at_commit import ImplementationAtCommit
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos import (
    create_implementation_at_commit_repo,
    create_repo_dashboard_repo,
    create_spec_tree_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.repo_dashboard_repo import RepoDashboardRepo


class RepoSidebarFacade:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = create_repo_dashboard_repo(session)
        self._impl_repo = create_implementation_at_commit_repo(session)
        self._tree_repo = create_spec_tree_repo(session)
        self._spec_version_repo = create_spec_version_repo(session)

    def get_sidebar(self, *, repo_id: int) -> RepoSidebarResponse:
        if self._repo.get_repo(repo_id) is None:
            raise HTTPException(status_code=404, detail="repo not found")

        version_rows = self._repo.list_specs_latest_versions(repo_id=repo_id)
        specs: list[SidebarSpec] = []

        for row in version_rows:
            display_title = row.version.title or row.spec.paper_id
            evaluation_commits = self._list_evaluation_commits_for_spec(
                repo_id=repo_id,
                spec_id=row.spec.id,
            )
            versions = [
                SidebarSpecVersion(
                    version_id=self._effective_version_id(
                        spec_id=row.spec.id,
                        commit_id=commit.id,
                    ),
                    commit_sha=commit.commit_sha,
                    commit_message=commit.commit_message,
                    committed_at=commit.committed_at,
                    title=self._effective_version_title(
                        spec_id=row.spec.id,
                        commit_id=commit.id,
                    ),
                    status=self._commit_status(
                        spec_id=row.spec.id,
                        commit_id=commit.id,
                    ),
                )
                for commit in evaluation_commits
            ]

            specs.append(
                SidebarSpec(
                    id=row.spec.id,
                    paper_id=row.spec.paper_id,
                    title=display_title,
                    versions=versions,
                )
            )

        return RepoSidebarResponse(specs=specs)

    def _list_evaluation_commits_for_spec(self, *, repo_id: int, spec_id: int) -> list[Commit]:
        stmt = (
            select(Commit)
            .join(ImplementationAtCommit, ImplementationAtCommit.commit_id == Commit.id)
            .join(SpecItem, SpecItem.id == ImplementationAtCommit.spec_item_id)
            .join(SpecVersion, SpecVersion.id == SpecItem.spec_version_id)
            .where(
                Commit.repo_id == repo_id,
                SpecVersion.spec_id == spec_id,
            )
            .group_by(Commit.id)
            .order_by(desc(Commit.committed_at), desc(Commit.id))
        )
        return list(self._session.scalars(stmt).all())

    def _effective_version_id(self, *, spec_id: int, commit_id: int) -> int:
        version = self._spec_version_repo.get_latest_at_or_before_commit(
            spec_id=spec_id,
            commit_id=commit_id,
        )
        if version is None:
            return 0
        return version.id

    def _effective_version_title(self, *, spec_id: int, commit_id: int) -> str | None:
        version = self._spec_version_repo.get_latest_at_or_before_commit(
            spec_id=spec_id,
            commit_id=commit_id,
        )
        if version is None:
            return None
        return version.title

    def _commit_status(self, *, spec_id: int, commit_id: int) -> str:
        version = self._spec_version_repo.get_latest_at_or_before_commit(
            spec_id=spec_id,
            commit_id=commit_id,
        )
        if version is None:
            return "unknown"

        items = self._tree_repo.list_items_for_versions(spec_version_ids=[version.id])
        return self._version_status(items=items, commit_id=commit_id)

    def _version_status(self, *, items: list, commit_id: int) -> str:
        tracked = [
            item
            for item in items
            if RepoDashboardRepo.is_tracked_importance(item.importance)
        ]
        if not tracked:
            return "unknown"

        evaluations: list[tuple] = []
        for item in tracked:
            implementation = self._impl_repo.get_for_spec_item_at_commit(
                spec_item_id=item.id,
                commit_id=commit_id,
            )
            if implementation is not None:
                evaluations.append((item, implementation))

        if not evaluations:
            return "unknown"

        must_missing = any(
            not implementation.implemented and item.importance == SpecItemImportance.MUST
            for item, implementation in evaluations
        )
        if must_missing:
            return "at_risk"

        implemented_count = sum(1 for _, implementation in evaluations if implementation.implemented)
        if implemented_count == len(evaluations):
            return "good"

        if implemented_count >= len(evaluations) * 0.5:
            return "good"

        return "at_risk"
