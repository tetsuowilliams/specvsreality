"""Assemble the spec tree response from the read repositories."""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.schemas.spec_tree import (
    SpecTreeImplementation,
    SpecTreeImplementsArtifact,
    SpecTreeItem,
    SpecTreeResponse,
    SpecTreeVersion,
)
from specvsreality_repositories.repos import create_spec_repo, create_spec_tree_repo


class SpecTreeFacade:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_tree(self, *, repo_id: int, spec_id: int) -> SpecTreeResponse:
        spec = create_spec_repo(self._session).get_by_id(spec_id)
        if spec is None or spec.repo_id != repo_id:
            raise HTTPException(status_code=404, detail="spec not found")

        tree_repo = create_spec_tree_repo(self._session)

        versions = tree_repo.list_versions_with_commit(spec_id=spec_id)
        version_ids = [version.id for version, _ in versions]

        items = tree_repo.list_items_for_versions(spec_version_ids=version_ids)
        items_by_version: dict[int, list] = defaultdict(list)
        for item in items:
            items_by_version[item.spec_version_id].append(item)

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

        version_blocks: list[SpecTreeVersion] = []
        for version, version_commit in versions:
            item_blocks: list[SpecTreeItem] = []
            for item in items_by_version.get(version.id, []):
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
                    SpecTreeItem(
                        id=item.id,
                        local_key=item.local_key,
                        item_type=item.item_type.value,
                        importance=item.importance.value,
                        text=item.text,
                        source_quote=item.source_quote,
                        success_criteria=list(item.success_criteria or []),
                        failure_criteria=list(item.failure_criteria or []),
                        implementations=implementation_blocks,
                    )
                )

            version_blocks.append(
                SpecTreeVersion(
                    id=version.id,
                    commit_sha=version_commit.commit_sha,
                    commit_message=version_commit.commit_message,
                    committed_at=version_commit.committed_at,
                    title=version.title,
                    summary=version.summary,
                    spec_md=version.spec_md,
                    tasks_md=version.tasks_md,
                    plan_md=version.plan_md,
                    items=item_blocks,
                )
            )

        return SpecTreeResponse(id=spec.id, paper_id=spec.paper_id, versions=version_blocks)
