"""Stage 4: evaluate whether candidate artifacts implement each spec item."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence

from specvsreality_repositories.repos import (
    ArtifactVersionRepo,
    ImplementationAtCommitRepo,
    ImplementsRepo,
)
from specvsreality_worker.agents.implements_agent import (
    CandidateArtifactContent,
    ImplementsAgent,
    SpecItemEvaluation,
    SpecItemForEvaluation,
)
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder
from specvsreality_worker.core.candidate_discovery import ResolvedCandidate
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.spec_merge import SpecWork

logger = logging.getLogger(__name__)


def _chunk(items: Sequence[SpecItemForEvaluation], size: int) -> list[list[SpecItemForEvaluation]]:
    return [list(items[start : start + size]) for start in range(0, len(items), size)]


class ImplementsEvaluation:
    def __init__(
        self,
        *,
        implements_agent: ImplementsAgent,
        implementation_at_commit_repo: ImplementationAtCommitRepo,
        implements_repo: ImplementsRepo,
        artifact_version_repo: ArtifactVersionRepo,
        settings: WorkerSettings,
    ) -> None:
        self._implements_agent = implements_agent
        self._implementation_at_commit_repo = implementation_at_commit_repo
        self._implements_repo = implements_repo
        self._artifact_version_repo = artifact_version_repo
        self._settings = settings

    def evaluate(
        self,
        *,
        commit: CommitContext,
        work: SpecWork,
        candidates: Sequence[ResolvedCandidate],
        metrics: AgentMetricsRecorder | None = None,
    ) -> None:
        asyncio.run(
            self._evaluate_async(
                commit=commit,
                work=work,
                candidates=candidates,
                metrics=metrics,
            ),
        )

    async def _evaluate_async(
        self,
        *,
        commit: CommitContext,
        work: SpecWork,
        candidates: Sequence[ResolvedCandidate],
        metrics: AgentMetricsRecorder | None = None,
    ) -> None:
        if not work.spec_items:
            return

        valid_item_ids = {item.id for item in work.spec_items}
        max_chars = self._settings.implements_agent_max_artifact_chars
        candidate_contents = [
            CandidateArtifactContent(
                filepath=candidate.filepath,
                content=candidate.content[:max_chars],
            )
            for candidate in candidates
        ]
        artifact_version_by_filepath = {
            candidate.filepath: candidate.artifact_version_id for candidate in candidates
        }

        eval_items = [
            SpecItemForEvaluation(
                spec_item_id=item.id,
                local_key=item.local_key,
                item_type=item.item_type.value,
                text=item.text,
                success_criteria=list(item.success_criteria or []),
                failure_criteria=list(item.failure_criteria or []),
            )
            for item in work.spec_items
        ]

        batch_size = self._settings.implements_agent_batch_size
        batches = _chunk(eval_items, batch_size)
        concurrency = self._settings.implements_agent_concurrent_batches
        semaphore = asyncio.Semaphore(concurrency)

        async def run_batch(batch: list[SpecItemForEvaluation]) -> list[SpecItemEvaluation]:
            async with semaphore:
                return await self._implements_agent.evaluate_batch(
                    spec_label=work.spec_label,
                    spec_items=batch,
                    candidates=candidate_contents,
                    spec_md=work.spec_md,
                    tasks_md=work.tasks_md,
                    plan_md=work.plan_md,
                    metrics=metrics,
                )

        logger.info(
            "implements evaluate start spec=%s items=%s batches=%s batch_size=%s concurrency=%s",
            work.spec_label,
            len(eval_items),
            len(batches),
            batch_size,
            concurrency,
        )

        batch_results = await asyncio.gather(*(run_batch(batch) for batch in batches))

        for evaluations in batch_results:
            for evaluation in evaluations:
                if evaluation.spec_item_id not in valid_item_ids:
                    logger.warning(
                        "evaluation references unknown spec_item_id=%s spec=%s commit=%s; skipping",
                        evaluation.spec_item_id,
                        work.spec_label,
                        commit.commit_sha[:7],
                    )
                    continue
                self._persist_evaluation(
                    commit=commit,
                    evaluation=evaluation,
                    artifact_version_by_filepath=artifact_version_by_filepath,
                )

    def _persist_evaluation(
        self,
        *,
        commit: CommitContext,
        evaluation: SpecItemEvaluation,
        artifact_version_by_filepath: dict[str, int],
    ) -> None:
        implementation = self._implementation_at_commit_repo.upsert_evaluation(
            spec_item_id=evaluation.spec_item_id,
            commit_id=commit.commit_id,
            implemented=evaluation.implemented,
            summary=evaluation.summary,
            gaps=evaluation.gaps,
            confidence=evaluation.confidence,
        )

        for evidence in evaluation.implemented_by:
            filepath = evidence.artifact_id.replace("\\", "/").strip()
            artifact_version_id = artifact_version_by_filepath.get(filepath)
            if artifact_version_id is None:
                artifact_version = self._artifact_version_repo.get_by_filepath_and_commit(
                    filepath=filepath,
                    commit_id=commit.commit_id,
                )
                if artifact_version is None:
                    logger.warning(
                        "skip implements evidence spec_item_id=%s filepath=%s "
                        "(not a known candidate or artifact version)",
                        evaluation.spec_item_id,
                        filepath,
                    )
                    continue
                artifact_version_id = artifact_version.id

            self._implements_repo.upsert_evidence(
                implementation_at_commit_id=implementation.id,
                artifact_version_id=artifact_version_id,
                evidence_file=filepath,
                evidence_line_number=evidence.evidence_line_number,
                evidence_snippet=evidence.evidence_snippet,
                evidence_relevance=evidence.evidence_relevance,
            )
