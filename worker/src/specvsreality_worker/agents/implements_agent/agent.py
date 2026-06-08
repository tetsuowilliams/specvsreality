from __future__ import annotations

import concurrent.futures
import logging
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

import opik
from pydantic_ai import Agent

from specvsreality_repositories.models.enums import AgentName

from specvsreality_worker.agents.implements_agent.models import (
    CandidateArtifactContent,
    ImplementsBatchResult,
    SpecItemEvaluation,
    SpecItemForEvaluation,
)
from specvsreality_worker.agents.implements_agent.prompts import SYSTEM_PROMPT, build_batch_prompt
from specvsreality_worker.agents.pydantic_ai_verbose import build_event_stream_handler
from specvsreality_worker.config import WorkerSettings

if TYPE_CHECKING:
    from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder

_OPIK_PROJECT = "specvsreality-worker"
logger = logging.getLogger(__name__)


class ImplementsAgent:
    """LLM-backed batch evaluation of whether candidate artifacts implement spec items."""

    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._agent: Agent[None, ImplementsBatchResult] = Agent(
            model=settings.implements_agent_model,
            output_type=ImplementsBatchResult,
            system_prompt=SYSTEM_PROMPT,
        )

    @opik.track(
        name="implements-agent",
        project_name=_OPIK_PROJECT,
        tags=["agent:implements"],
        ignore_arguments=("spec_md", "tasks_md", "plan_md", "candidates"),
    )
    def evaluate_batch(
        self,
        *,
        spec_label: str,
        spec_items: Sequence[SpecItemForEvaluation],
        candidates: Sequence[CandidateArtifactContent],
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        metrics: AgentMetricsRecorder | None = None,
    ) -> list[SpecItemEvaluation]:
        if not spec_items:
            return []

        prompt = build_batch_prompt(
            spec_items=spec_items,
            candidates=candidates,
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
        )
        timeout_s = self._settings.implements_agent_timeout_seconds
        usage_limits = self._settings.implements_usage_limits()
        logger.info(
            "implements evaluate_batch start spec=%s spec_items=%s candidates=%s timeout_s=%s",
            spec_label,
            len(spec_items),
            len(candidates),
            timeout_s,
        )
        started = time.monotonic()

        def _run_agent() -> object:
            return self._agent.run_sync(
                prompt,
                usage_limits=usage_limits,
                event_stream_handler=build_event_stream_handler(self._settings),
            )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_agent)
            try:
                result = future.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError as exc:
                elapsed_s = time.monotonic() - started
                logger.error(
                    "implements evaluate_batch timed out spec=%s elapsed_s=%.1f timeout_s=%s",
                    spec_label,
                    elapsed_s,
                    timeout_s,
                )
                raise TimeoutError(
                    f"implements evaluation timed out after {timeout_s}s (spec={spec_label!r})",
                ) from exc

        elapsed_s = time.monotonic() - started
        if metrics is not None:
            metrics.record(
                agent=AgentName.IMPLEMENTS,
                model=self._settings.implements_agent_model,
                usage=result.usage(),
                ran_at=result.timestamp(),
            )
        evaluations = result.output.evaluations
        logger.info(
            "implements evaluate_batch done spec=%s elapsed_s=%.1f evaluations=%s",
            spec_label,
            elapsed_s,
            len(evaluations),
        )
        return evaluations


def create_implements_agent(settings: WorkerSettings) -> ImplementsAgent:
    return ImplementsAgent(settings)
