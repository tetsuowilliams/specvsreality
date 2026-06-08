"""Assemble compact sidebar response."""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.schemas.repo_sidebar import (
    RepoSidebarResponse,
    SidebarSpec,
    SidebarSpecVersion,
)
from specvsreality_repositories.models.enums import SpecItemImportance
from specvsreality_repositories.repos import (
    create_implementation_at_commit_repo,
    create_repo_dashboard_repo,
)
from specvsreality_repositories.repos.repo_dashboard_repo import RepoDashboardRepo


class RepoSidebarFacade:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = create_repo_dashboard_repo(session)
        self._impl_repo = create_implementation_at_commit_repo(session)

    def get_sidebar(self, *, repo_id: int) -> RepoSidebarResponse:
        if self._repo.get_repo(repo_id) is None:
            raise HTTPException(status_code=404, detail="repo not found")

        version_rows = self._repo.list_all_spec_versions_for_repo(repo_id=repo_id)
        version_ids = [row.version.id for row in version_rows]
        items = self._repo.list_items_for_versions(version_ids=version_ids)
        items_by_version: dict[int, list] = defaultdict(list)
        for item in items:
            items_by_version[item.spec_version_id].append(item)

        specs_by_id: dict[int, list] = defaultdict(list)
        for row in version_rows:
            specs_by_id[row.spec.id].append(row)

        specs: list[SidebarSpec] = []
        for spec_id, rows in sorted(
            specs_by_id.items(),
            key=lambda entry: (entry[1][0].spec.paper_id, entry[0]),
        ):
            spec = rows[0].spec
            latest = rows[0]
            display_title = latest.version.title or spec.paper_id

            versions = [
                SidebarSpecVersion(
                    version_id=row.version.id,
                    commit_sha=row.commit.commit_sha,
                    commit_message=row.commit.commit_message,
                    committed_at=row.commit.committed_at,
                    title=row.version.title,
                    status=self._version_status(
                        items=items_by_version.get(row.version.id, []),
                        commit_id=row.commit.id,
                    ),
                )
                for row in rows
            ]

            specs.append(
                SidebarSpec(
                    id=spec_id,
                    paper_id=spec.paper_id,
                    title=display_title,
                    versions=versions,
                )
            )

        return RepoSidebarResponse(specs=specs)

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
