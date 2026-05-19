"""Per-commit step: evaluate active requirement versions against code blobs."""

from __future__ import annotations

import logging

from specvsreality_repositories.models.repository import Repository
from specvsreality_repositories.repos import CommitFileRepo
from specvsreality_worker.domain import CommitRecord, TreeEntry
from specvsreality_worker.evaluation import (
    ClaimGate,
    ImplementationEvaluator,
    RequirementContextResolver,
)
from specvsreality_worker.ingestion_config import EvaluationConfig

logger = logging.getLogger(__name__)


class EvaluationStep:
    """For one commit: pair every active requirement with every code blob.

    Each pair passes through :class:`ClaimGate` (dedup + heuristic) before the
    LLM is invoked. The LLM call and claim insert happen inside
    :class:`ImplementationEvaluator`; this class only owns flow.
    """

    def __init__(
        self,
        *,
        requirement_context_resolver: RequirementContextResolver,
        commit_file_repo: CommitFileRepo,
        claim_gate: ClaimGate,
        implementation_evaluator: ImplementationEvaluator,
        config: EvaluationConfig,
    ) -> None:
        self._context = requirement_context_resolver
        self._commit_file_repo = commit_file_repo
        self._gate = claim_gate
        self._evaluator = implementation_evaluator
        self._config = config

    def process(
        self,
        *,
        repository: Repository,
        commit: CommitRecord,
        tree: list[TreeEntry],
    ) -> None:
        active = self._context.active_at(repository=repository, commit=commit)
        if not active:
            return

        spec_paths = self._config.spec_file_paths(tree)
        code_blobs = self._commit_file_repo.code_blobs_at_commit(
            commit_sha=commit.sha, exclude_paths=spec_paths
        )
        if not code_blobs:
            return

        # Build a path/size lookup so the cheap filter has hints without a
        # second DB round-trip per pair.
        size_by_blob = {e.blob_sha: e.size_bytes for e in tree}
        path_by_blob = {e.blob_sha: e.path for e in tree if e.path not in spec_paths}

        for requirement_version in active:
            for blob_sha in code_blobs:
                if not self._gate.needs_evaluation(
                    requirement_version=requirement_version,
                    blob_sha=blob_sha,
                    blob_size_bytes=size_by_blob.get(blob_sha),
                    path_hint=path_by_blob.get(blob_sha),
                ):
                    continue
                self._evaluator.evaluate(
                    requirement_version=requirement_version,
                    blob_sha=blob_sha,
                    path_hint=path_by_blob.get(blob_sha),
                )
        logger.debug(
            "evaluation step done sha=%s active=%d code_blobs=%d",
            commit.sha[:7],
            len(active),
            len(code_blobs),
        )
