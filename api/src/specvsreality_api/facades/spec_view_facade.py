"""Assemble the spec markdown view response."""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.core.spec_text_match import find_item_span
from specvsreality_api.schemas.spec_tree import SpecTreeImplementation, SpecTreeImplementsArtifact
from specvsreality_api.schemas.spec_view import (
    SpecViewItem,
    SpecViewItemSpan,
    SpecViewItemSpans,
    SpecViewResponse,
    SpecViewSummary,
    SpecViewVersion,
)
from specvsreality_repositories.models.enums import SpecItemImportance
from specvsreality_repositories.repos.repo_dashboard_repo import RepoDashboardRepo
from specvsreality_repositories.repos import (
    create_commit_repo,
    create_spec_repo,
    create_spec_tree_repo,
)


class SpecViewFacade:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_view(
        self,
        *,
        repo_id: int,
        spec_id: int,
        commit_sha: str | None = None,
    ) -> SpecViewResponse:
        spec = create_spec_repo(self._session).get_by_id(spec_id)
        if spec is None or spec.repo_id != repo_id:
            raise HTTPException(status_code=404, detail="spec not found")

        tree_repo = create_spec_tree_repo(self._session)
        versions = tree_repo.list_versions_with_commit(spec_id=spec_id)
        if not versions:
            raise HTTPException(status_code=404, detail="no spec versions found")

        if commit_sha is not None:
            version_row = self._version_for_commit(repo_id=repo_id, spec_id=spec_id, commit_sha=commit_sha)
            if version_row is None:
                raise HTTPException(status_code=404, detail="spec version not found for commit")
            version, version_commit = version_row
        else:
            version, version_commit = versions[-1]

        items = tree_repo.list_items_for_versions(spec_version_ids=[version.id])
        item_ids = [item.id for item in items]

        implementations = tree_repo.list_implementations_with_commit(spec_item_ids=item_ids)
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
                spec_md=version.spec_md,
                tasks_md=version.tasks_md,
                plan_md=version.plan_md,
                source_quote=item.source_quote,
                text=item.text,
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

        summary = self._build_summary(item_blocks)

        return SpecViewResponse(
            id=spec.id,
            paper_id=spec.paper_id,
            summary=summary,
            version=SpecViewVersion(
                id=version.id,
                commit_sha=version_commit.commit_sha,
                commit_message=version_commit.commit_message,
                committed_at=version_commit.committed_at,
                title=version.title,
                summary=version.summary,
                spec_md=version.spec_md,
                tasks_md=version.tasks_md,
                plan_md=version.plan_md,
            ),
            items=item_blocks,
        )

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
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        source_quote: str,
        text: str,
    ) -> SpecViewItemSpans:
        def _span_for(markdown: str | None) -> SpecViewItemSpan | None:
            if not markdown:
                return None
            match = find_item_span(
                markdown,
                source_quote=source_quote,
                text=text,
            )
            if match is None:
                return None
            return SpecViewItemSpan(start=match[0], end=match[1])

        return SpecViewItemSpans(
            spec=_span_for(spec_md),
            tasks=_span_for(tasks_md),
            plan=_span_for(plan_md),
        )

    def _version_for_commit(
        self,
        *,
        repo_id: int,
        spec_id: int,
        commit_sha: str,
    ) -> tuple | None:
        commit = create_commit_repo(self._session).get_by_sha(
            repo_id=repo_id,
            commit_sha=commit_sha,
        )
        if commit is None:
            return None

        tree_repo = create_spec_tree_repo(self._session)
        for version, version_commit in tree_repo.list_versions_with_commit(spec_id=spec_id):
            if version_commit.id == commit.id:
                return version, version_commit
        return None
