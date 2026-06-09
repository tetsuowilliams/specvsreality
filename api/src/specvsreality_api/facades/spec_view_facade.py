"""Assemble the spec markdown view response."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from fastapi import HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.schemas.spec_tree import SpecTreeImplementation, SpecTreeImplementsArtifact
from specvsreality_api.schemas.spec_view import (
    SpecViewItem,
    SpecViewItemSpan,
    SpecViewItemSpans,
    SpecViewMarkdownResponse,
    SpecViewOverviewResponse,
    SpecViewSummary,
    SpecViewVersionMeta,
)
from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.enums import SpecItemImportance
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos import (
    create_commit_repo,
    create_spec_repo,
    create_spec_tree_repo,
)
from specvsreality_repositories.repos.repo_dashboard_repo import RepoDashboardRepo
from specvsreality_repositories.text_match import find_item_span


@dataclass(frozen=True, slots=True)
class _ResolvedVersion:
    version: SpecVersion
    commit: Commit
    evaluation_commit: Commit


class SpecViewFacade:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_overview(
        self,
        *,
        repo_id: int,
        spec_id: int,
        commit_sha: str | None = None,
    ) -> SpecViewOverviewResponse:
        spec = create_spec_repo(self._session).get_by_id(spec_id)
        if spec is None or spec.repo_id != repo_id:
            raise HTTPException(status_code=404, detail="spec not found")

        resolved = self._resolve_version(repo_id=repo_id, spec_id=spec_id, commit_sha=commit_sha)
        version = resolved.version
        version_commit = resolved.commit

        tree_repo = create_spec_tree_repo(self._session)
        items = tree_repo.list_items_for_versions(spec_version_ids=[version.id])
        item_blocks = self._build_item_blocks(
            items=items,
            version=version,
            commit_id=resolved.evaluation_commit.id,
        )
        summary = self._build_summary(item_blocks)

        return SpecViewOverviewResponse(
            id=spec.id,
            paper_id=spec.paper_id,
            summary=summary,
            version=SpecViewVersionMeta(
                id=version.id,
                commit_sha=version_commit.commit_sha,
                commit_message=version_commit.commit_message,
                committed_at=version_commit.committed_at,
                title=version.title,
                summary=version.summary,
                has_tasks_md=bool(version.tasks_md and version.tasks_md.strip()),
                has_plan_md=bool(version.plan_md and version.plan_md.strip()),
            ),
            items=item_blocks,
        )

    def get_markdown(
        self,
        *,
        repo_id: int,
        spec_id: int,
        commit_sha: str | None = None,
    ) -> SpecViewMarkdownResponse:
        spec = create_spec_repo(self._session).get_by_id(spec_id)
        if spec is None or spec.repo_id != repo_id:
            raise HTTPException(status_code=404, detail="spec not found")

        resolved = self._resolve_version(repo_id=repo_id, spec_id=spec_id, commit_sha=commit_sha)
        version = resolved.version

        return SpecViewMarkdownResponse(
            spec_md=version.spec_md,
            tasks_md=version.tasks_md,
            plan_md=version.plan_md,
        )

    def _resolve_version(
        self,
        *,
        repo_id: int,
        spec_id: int,
        commit_sha: str | None,
    ) -> _ResolvedVersion:
        tree_repo = create_spec_tree_repo(self._session)

        if commit_sha is not None:
            evaluation_commit = create_commit_repo(self._session).get_by_sha(
                repo_id=repo_id,
                commit_sha=commit_sha,
            )
            if evaluation_commit is None:
                raise HTTPException(status_code=404, detail="spec version not found for commit")

            version_row = tree_repo.get_latest_version_with_commit_at_or_before_commit(
                spec_id=spec_id,
                commit_id=evaluation_commit.id,
            )
            if version_row is None:
                raise HTTPException(status_code=404, detail="spec version not found for commit")
            version, version_commit = version_row
            return _ResolvedVersion(
                version=version,
                commit=version_commit,
                evaluation_commit=evaluation_commit,
            )

        version_row = tree_repo.get_latest_version_with_commit(spec_id=spec_id)
        if version_row is None:
            raise HTTPException(status_code=404, detail="no spec versions found")
        version, version_commit = version_row
        return _ResolvedVersion(
            version=version,
            commit=version_commit,
            evaluation_commit=version_commit,
        )

    def _build_item_blocks(
        self,
        *,
        items: list[SpecItem],
        version: SpecVersion,
        commit_id: int,
    ) -> list[SpecViewItem]:
        tree_repo = create_spec_tree_repo(self._session)
        item_ids = [item.id for item in items]

        implementations = tree_repo.list_implementations_with_commit(
            spec_item_ids=item_ids,
            commit_id=commit_id,
        )
        impls_by_item: dict[int, list] = defaultdict(list)
        for implementation, commit in implementations:
            impls_by_item[implementation.spec_item_id].append((implementation, commit))

        impl_ids = [implementation.id for implementation, _ in implementations]
        implements_rows = tree_repo.list_implements_with_artifacts(
            implementation_at_commit_ids=impl_ids,
        )
        artifacts_by_impl: dict[int, list[SpecTreeImplementsArtifact]] = defaultdict(list)
        for implements, artifact_version, artifact in implements_rows:
            artifacts_by_impl[implements.implementation_at_commit_id].append(
                SpecTreeImplementsArtifact(
                    artifact_version_id=artifact_version.id,
                    filepath=artifact.filepath,
                    evidence_file=implements.evidence_file,
                    evidence_line_number=implements.evidence_line_number,
                    evidence_snippet=implements.evidence_snippet,
                    evidence_relevance=implements.evidence_relevance,
                )
            )

        item_blocks: list[SpecViewItem] = []
        for item in items:
            spans = self._item_spans(
                item=item,
                spec_md=version.spec_md,
                tasks_md=version.tasks_md,
                plan_md=version.plan_md,
            )
            implementation_blocks = [
                SpecTreeImplementation(
                    id=implementation.id,
                    commit_sha=commit.commit_sha,
                    commit_message=commit.commit_message,
                    committed_at=commit.committed_at,
                    implemented=implementation.implemented,
                    summary=implementation.summary,
                    gaps=list(implementation.gaps or []),
                    confidence=implementation.confidence,
                    artifacts=artifacts_by_impl.get(implementation.id, []),
                )
                for implementation, commit in impls_by_item.get(item.id, [])
            ]
            item_blocks.append(
                SpecViewItem(
                    id=item.id,
                    local_key=item.local_key,
                    item_type=item.item_type.value,
                    importance=item.importance.value,
                    text=item.text,
                    source_quote=item.source_quote,
                    spans=spans,
                    success_criteria=list(item.success_criteria or []),
                    failure_criteria=list(item.failure_criteria or []),
                    implementations=implementation_blocks,
                )
            )

        return item_blocks

    def _build_summary(self, items: list[SpecViewItem]) -> SpecViewSummary:
        tracked = [
            item
            for item in items
            if item.importance in {SpecItemImportance.MUST.value, SpecItemImportance.SHOULD.value}
        ]
        evaluated = 0
        implemented = 0
        mandatory_gaps = 0
        low_confidence = 0

        for item in tracked:
            latest = self._latest_implementation(item)
            if latest is None:
                continue
            evaluated += 1
            if latest.implemented:
                implemented += 1
            elif item.importance == SpecItemImportance.MUST.value:
                mandatory_gaps += 1
            if RepoDashboardRepo.is_low_confidence(latest.confidence):
                low_confidence += 1

        unevaluated = len(tracked) - evaluated
        coverage = (
            round((implemented / evaluated) * 100, 1)
            if evaluated > 0
            else None
        )

        if evaluated == 0:
            status = "unknown"
        elif mandatory_gaps > 0:
            status = "at_risk"
        elif implemented == evaluated and tracked:
            status = "good"
        elif implemented >= evaluated * 0.5:
            status = "mostly_implemented"
        else:
            status = "at_risk"

        return SpecViewSummary(
            total_items=len(items),
            tracked_items=len(tracked),
            evaluated=evaluated,
            implemented=implemented,
            mandatory_gaps=mandatory_gaps,
            low_confidence=low_confidence,
            unevaluated=unevaluated,
            coverage_percent=coverage,
            status=status,
        )

    @staticmethod
    def _latest_implementation(item: SpecViewItem) -> SpecTreeImplementation | None:
        if not item.implementations:
            return None
        return max(item.implementations, key=lambda impl: impl.committed_at)

    def _item_spans(
        self,
        *,
        item: SpecItem,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
    ) -> SpecViewItemSpans:
        cached = item.highlight_spans or {}

        def _span_for(document: str, markdown: str | None) -> SpecViewItemSpan | None:
            if not markdown:
                return None

            stored = cached.get(document)
            if isinstance(stored, dict):
                start = stored.get("start")
                end = stored.get("end")
                if isinstance(start, int) and isinstance(end, int) and 0 <= start < end <= len(markdown):
                    return SpecViewItemSpan(start=start, end=end)

            match = find_item_span(
                markdown,
                source_quote=item.source_quote,
                text=item.text,
            )
            if match is None:
                return None
            return SpecViewItemSpan(start=match[0], end=match[1])

        return SpecViewItemSpans(
            spec=_span_for("spec", spec_md),
            tasks=_span_for("tasks", tasks_md),
            plan=_span_for("plan", plan_md),
        )
