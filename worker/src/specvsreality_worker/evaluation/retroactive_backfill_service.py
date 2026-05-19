"""Evaluate one new requirement version against ALL historical blobs."""

from __future__ import annotations

import logging

from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.repos import BlobRepo
from specvsreality_worker.evaluation.claim_gate import ClaimGate
from specvsreality_worker.evaluation.implementation_evaluator import (
    ImplementationEvaluator,
)

logger = logging.getLogger(__name__)


class RetroactiveBackfillService:
    """Catch deleted-code matches that the forward walk would miss.

    When a new requirement version appears at commit C50, the forward
    evaluation only sees blobs present at C50. If a relevant file was deleted
    at C30, no claim would ever be written. Running this service after a new
    requirement version is created evaluates every known blob, so retroactive
    queries against historical commits surface the prior implementation.
    """

    def __init__(
        self,
        *,
        blob_repo: BlobRepo,
        claim_gate: ClaimGate,
        implementation_evaluator: ImplementationEvaluator,
    ) -> None:
        self._blob_repo = blob_repo
        self._gate = claim_gate
        self._evaluator = implementation_evaluator

    def backfill(self, *, requirement_version: RequirementVersion) -> int:
        """Return the number of new claims written."""
        written = 0
        for blob_sha in self._blob_repo.all_shas():
            if not self._gate.needs_evaluation(
                requirement_version=requirement_version,
                blob_sha=blob_sha,
            ):
                continue
            self._evaluator.evaluate(
                requirement_version=requirement_version,
                blob_sha=blob_sha,
            )
            written += 1
        logger.info(
            "retroactive backfill rv=%s wrote=%s",
            requirement_version.id,
            written,
        )
        return written
