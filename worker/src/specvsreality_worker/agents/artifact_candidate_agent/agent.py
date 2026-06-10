from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Sequence
from typing import TYPE_CHECKING

import opik
from pydantic_ai.tool_manager import ToolManager

from specvsreality_repositories.models.enums import AgentName
from specvsreality_worker.agents.artifact_candidate_agent.agent_builder import (
    build_artifact_candidate_agent,
)
from specvsreality_worker.agents.artifact_candidate_agent.deps import CommitToolDeps
from specvsreality_worker.agents.artifact_candidate_agent.models import (
    ArtifactCandidateResult,
    SpecItemContext,
)
from specvsreality_worker.agents.artifact_candidate_agent.prompts import build_discovery_prompt
from specvsreality_worker.agents.artifact_candidate_agent.tool_cache import CommitToolCache
from specvsreality_worker.agents.pydantic_ai_verbose import build_event_stream_handler
from specvsreality_worker.config import WorkerSettings

if TYPE_CHECKING:
    from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder
    from specvsreality_worker.git_adapter import GitAdapter

_OPIK_PROJECT = "specvsreality-worker"
logger = logging.getLogger(__name__)


class ArtifactCandidateAgent:
    """LLM-backed discovery of files that may implement a spec at a commit."""

    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._agent = build_artifact_candidate_agent(settings)

    @opik.track(
        name="artifact-candidate-agent",
        project_name=_OPIK_PROJECT,
        tags=["agent:artifact-candidate"],
        ignore_arguments=("spec_md", "tasks_md", "plan_md"),
    )
    def discover(
        self,
        *,
        git_adapter: GitAdapter,
        commit_sha: str,
        spec_label: str,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        spec_items: Sequence[SpecItemContext],
        tool_cache: CommitToolCache | None = None,
        metrics: AgentMetricsRecorder | None = None,
    ) -> ArtifactCandidateResult:
        return asyncio.run(
            self.discover_async(
                git_adapter=git_adapter,
                commit_sha=commit_sha,
                spec_label=spec_label,
                spec_md=spec_md,
                tasks_md=tasks_md,
                plan_md=plan_md,
                spec_items=spec_items,
                tool_cache=tool_cache,
                metrics=metrics,
            ),
        )

    async def discover_async(
        self,
        *,
        git_adapter: GitAdapter,
        commit_sha: str,
        spec_label: str,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        spec_items: Sequence[SpecItemContext],
        tool_cache: CommitToolCache | None = None,
        metrics: AgentMetricsRecorder | None = None,
    ) -> ArtifactCandidateResult:
        prompt = build_discovery_prompt(
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
            spec_items=spec_items,
        )
        deps = CommitToolDeps(
            git_adapter=git_adapter,
            commit_sha=commit_sha,
            label=spec_label,
            tool_cache=tool_cache,
            settings=self._settings,
        )
        timeout_s = self._settings.artifact_candidate_agent_timeout_seconds
        usage_limits = self._settings.artifact_candidate_usage_limits()
        logger.info(
            "artifact candidate discover start spec=%s commit=%s timeout_s=%s "
            "request_limit=%s tool_calls_limit=%s spec_items=%s",
            spec_label,
            commit_sha[:7],
            timeout_s,
            usage_limits.request_limit,
            usage_limits.tool_calls_limit,
            len(spec_items),
        )
        started = time.monotonic()

        try:
            with ToolManager.parallel_execution_mode("sequential"):
                result = await asyncio.wait_for(
                    self._agent.run(
                        prompt,
                        deps=deps,
                        usage_limits=usage_limits,
                        event_stream_handler=build_event_stream_handler(self._settings),
                    ),
                    timeout=timeout_s,
                )
        except TimeoutError as exc:
            elapsed_s = time.monotonic() - started
            logger.error(
                "artifact candidate discover timeout spec=%s commit=%s elapsed_s=%.1f to=%s",
                spec_label,
                commit_sha[:7],
                elapsed_s,
                timeout_s,
            )
            raise TimeoutError(
                f"artifact candidate discovery timed out after {timeout_s}s "
                f"(spec={spec_label!r}, commit={commit_sha[:7]})",
            ) from exc

        elapsed_s = time.monotonic() - started
        if metrics is not None:
            metrics.record(
                agent=AgentName.ARTIFACT_CANDIDATE,
                model=self._settings.artifact_candidate_agent_model,
                usage=result.usage(),
                ran_at=result.timestamp(),
            )
        output = result.output
        logger.info(
            "artifact candidate discover done spec=%s commit=%s elapsed_s=%.1f candidates=%s",
            spec_label,
            commit_sha[:7],
            elapsed_s,
            len(output.candidates),
        )
        return output


def create_artifact_candidate_agent(settings: WorkerSettings) -> ArtifactCandidateAgent:
    return ArtifactCandidateAgent(settings)
