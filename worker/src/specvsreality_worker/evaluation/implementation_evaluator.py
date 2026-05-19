"""Run the implements-evaluation agent for one (requirement_version, blob) pair."""

from __future__ import annotations

from specvsreality_repositories.models.implementation_claim import ImplementationClaim
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.repos import ImplementationClaimRepo, Verdict
from specvsreality_worker.agents.implements_agent import ImplementsEvaluationAgent
from specvsreality_worker.agents.implements_agent.models import ImplementsAssessment
from specvsreality_worker.ingestion_config import EvaluationConfig
from specvsreality_worker.support import BlobReader

_CONFIDENCE_BY_LABEL = {"high": 0.9, "medium": 0.6, "low": 0.3}


class ImplementationEvaluator:
    """Wrap :class:`ImplementsEvaluationAgent` to produce ``ImplementationClaim`` rows.

    Translates the agent's structured output into the persistence model:
    ``implements`` -> :class:`Verdict`, ``confidence`` label -> numeric value,
    and stamps the configured ``model_version`` / ``prompt_version``.

    The evaluator persists nothing on its own; it returns the inserted
    :class:`ImplementationClaim` from :class:`ImplementationClaimRepo` so the
    caller can decide whether to trigger downstream work.
    """

    def __init__(
        self,
        *,
        implements_evaluation_agent: ImplementsEvaluationAgent,
        blob_reader: BlobReader,
        claim_repo: ImplementationClaimRepo,
        config: EvaluationConfig,
    ) -> None:
        self._agent = implements_evaluation_agent
        self._blob_reader = blob_reader
        self._claim_repo = claim_repo
        self._config = config

    def evaluate(
        self,
        *,
        requirement_version: RequirementVersion,
        blob_sha: str,
        path_hint: str | None = None,
    ) -> ImplementationClaim:
        code_text = self._blob_reader.read_text(blob_sha)
        assessment = self._agent.evaluate(
            spec_md="",
            tasks_md=None,
            plan_md=None,
            requirement_id=None,
            requirement_text=requirement_version.content,
            artifact_sources=[(path_hint or blob_sha, code_text)],
        )
        verdict = self._verdict_for(assessment)
        confidence = _CONFIDENCE_BY_LABEL.get(assessment.confidence.lower())
        return self._claim_repo.insert(
            requirement_version_id=requirement_version.id,
            blob_sha=blob_sha,
            verdict=verdict.value,
            confidence=confidence,
            model_version=self._config.model_version,
            prompt_version=self._config.prompt_version,
            reasoning=assessment.reasoning,
        )

    @staticmethod
    def _verdict_for(assessment: ImplementsAssessment) -> Verdict:
        if assessment.implements:
            return Verdict.IMPLEMENTS
        if assessment.confidence.lower() == "low":
            return Verdict.UNCLEAR
        return Verdict.DOES_NOT_IMPLEMENT
