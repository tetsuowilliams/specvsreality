"""Combine model+prompt dedup with the cheap candidate filter."""

from __future__ import annotations

from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.repos import ImplementationClaimRepo
from specvsreality_worker.evaluation.candidate_filter import CandidateFilter
from specvsreality_worker.ingestion_config import EvaluationConfig


class ClaimGate:
    """Decide whether ``(requirement_version, blob)`` needs LLM evaluation.

    Order:

    1. If we already have a claim for this exact ``(rv, blob, model, prompt)``
       tuple, skip -- the answer would be identical.
    2. Otherwise consult the cheap heuristic in :class:`CandidateFilter`.

    Bumping ``model_version`` or ``prompt_version`` in :class:`EvaluationConfig`
    invalidates step (1) and forces re-evaluation.
    """

    def __init__(
        self,
        *,
        claim_repo: ImplementationClaimRepo,
        candidate_filter: CandidateFilter,
        config: EvaluationConfig,
    ) -> None:
        self._claim_repo = claim_repo
        self._candidate_filter = candidate_filter
        self._config = config

    def needs_evaluation(
        self,
        *,
        requirement_version: RequirementVersion,
        blob_sha: str,
        blob_size_bytes: int | None = None,
        path_hint: str | None = None,
    ) -> bool:
        already = self._claim_repo.has_claim(
            requirement_version_id=requirement_version.id,
            blob_sha=blob_sha,
            model_version=self._config.model_version,
            prompt_version=self._config.prompt_version,
        )
        if already:
            return False
        return self._candidate_filter.is_candidate(
            blob_size_bytes=blob_size_bytes,
            path_hint=path_hint,
            requirement_version=requirement_version,
        )
