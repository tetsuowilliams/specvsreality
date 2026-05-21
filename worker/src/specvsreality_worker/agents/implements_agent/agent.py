from __future__ import annotations

import concurrent.futures
import logging
import os
import time
from typing import TYPE_CHECKING

import opik
from pydantic_ai.tool_manager import ToolManager

from specvsreality_worker.agents.implements_agent.agent_builder import build_implements_agent
from specvsreality_worker.agents.implements_agent.deps import CommitToolDeps
from specvsreality_worker.agents.implements_agent.tool_cache import CommitToolCache
from specvsreality_worker.agents.implements_agent.models import RequirementJustification
from specvsreality_worker.agents.implements_agent.prompts import build_evaluation_prompt
from specvsreality_worker.agents.pydantic_ai_verbose import build_event_stream_handler
from specvsreality_worker.agents.implements_agent.settings import (
    implements_agent_timeout_seconds,
    implements_agent_usage_limits,
)

if TYPE_CHECKING:
    from specvsreality_worker.git_adapter import GitAdapter

_OPIK_PROJECT = "specvsreality-worker"
logger = logging.getLogger(__name__)


class ImplementsEvaluationAgent:
    """LLM-backed check that a repository snapshot implements a given requirement."""

    def __init__(self, model: str) -> None:
        self._agent = build_implements_agent(model)

    @opik.track(
        name="implements-evaluation-agent",
        project_name=_OPIK_PROJECT,
        tags=["agent:implements-evaluation"],
        ignore_arguments=("spec_md", "tasks_md", "plan_md"),
    )
    def evaluate(
        self,
        *,
        git_adapter: GitAdapter,
        commit_sha: str,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        requirement_id: str | None,
        requirement_text: str,
        path_globs: list[str] | None = None,
        tool_cache: CommitToolCache | None = None,
    ) -> RequirementJustification:
        if not requirement_text.strip():
            raise ValueError("requirement_text must be non-empty")

        globs = tuple(path_globs or ())
        prompt = build_evaluation_prompt(
            requirement_id=requirement_id,
            requirement_text=requirement_text,
            path_globs=path_globs,
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
        )
        deps = CommitToolDeps(
            git_adapter=git_adapter,
            commit_sha=commit_sha,
            requirement_id=requirement_id,
            path_globs=globs,
            tool_cache=tool_cache,
        )
        timeout_s = implements_agent_timeout_seconds()
        usage_limits = implements_agent_usage_limits()
        req_label = requirement_id or "(no id)"
        logger.info(
            "implements evaluate start requirement_id=%s commit=%s timeout_s=%s "
            "request_limit=%s tool_calls_limit=%s",
            req_label,
            commit_sha[:7],
            timeout_s,
            usage_limits.request_limit,
            usage_limits.tool_calls_limit,
        )
        started = time.monotonic()
        def _run_agent() -> object:
            # Parallel tool calls + per-tool thread pools caused worker-thread starvation
            # (tiny files like count.py appeared to "hang" for the full tool timeout).
            with ToolManager.parallel_execution_mode("sequential"):
                return self._agent.run_sync(
                    prompt,
                    deps=deps,
                    usage_limits=usage_limits,
                    event_stream_handler=build_event_stream_handler(),
                )

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(_run_agent)
            try:
                result = future.result(timeout=timeout_s)
            except concurrent.futures.TimeoutError as exc:
                elapsed_s = time.monotonic() - started
                logger.error(
                    "implements evaluate timed out requirement_id=%s commit=%s "
                    "elapsed_s=%.1f timeout_s=%s",
                    req_label,
                    commit_sha[:7],
                    elapsed_s,
                    timeout_s,
                )
                raise TimeoutError(
                    f"implements evaluation timed out after {timeout_s}s "
                    f"(requirement_id={req_label!r}, commit={commit_sha[:7]})",
                ) from exc
        elapsed_s = time.monotonic() - started
        output = result.output
        logger.info(
            "implements evaluate done requirement_id=%s commit=%s elapsed_s=%.1f "
            "implemented=%s confidence=%s evidence_count=%s",
            req_label,
            commit_sha[:7],
            elapsed_s,
            output.implemented,
            output.confidence,
            len(output.evidence),
        )
        return output


def create_implements_evaluation_agent() -> ImplementsEvaluationAgent:
    model = os.environ.get("IMPLEMENTS_AGENT_MODEL", "openai:gpt-4o-mini")
    return ImplementsEvaluationAgent(model=model)
