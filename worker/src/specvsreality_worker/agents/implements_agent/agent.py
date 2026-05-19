from __future__ import annotations

import os

import opik
from pydantic_ai import Agent

from specvsreality_worker.agents.implements_agent.models import ImplementsAssessment
from specvsreality_worker.observability import pydantic_ai_otlp_enabled

_OPIK_PROJECT = "specvsreality-worker"


class ImplementsEvaluationAgent:
    """LLM-backed check that an artifact's code implements a given requirement."""

    def __init__(self, model: str) -> None:
        self._agent = Agent(
            model=model,
            output_type=ImplementsAssessment,
            instrument=pydantic_ai_otlp_enabled,
            system_prompt=(
                "You are a senior engineer reviewing whether specific source code "
                "implements a single functional requirement. "
                "You are given spec-kit markdown (spec, tasks, plan) for background "
                "only; the authoritative statement of the requirement is the "
                "requirement text provided separately. "
                "Judge only what is visible in the supplied artifact sources. "
                "If critical behaviour is clearly delegated to code not shown, "
                "set implements to false or lower confidence and explain. "
                "Do not invent file contents or APIs that are not in the excerpt."
            ),
        )

    @opik.track(
        name="implements-evaluation-agent",
        project_name=_OPIK_PROJECT,
        tags=["agent:implements-evaluation"],
        ignore_arguments=("spec_md", "tasks_md", "plan_md"),
    )
    def evaluate(
        self,
        *,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        requirement_id: str | None,
        requirement_text: str,
        artifact_sources: list[tuple[str, str]],
    ) -> ImplementsAssessment:
        if not artifact_sources:
            raise ValueError("artifact_sources must contain at least one (path, source) pair")
        if not requirement_text.strip():
            raise ValueError("requirement_text must be non-empty")

        req_header = (
            f"Requirement ID: {requirement_id}\n" if requirement_id else "Requirement ID: (none)\n"
        )
        files_blocks = "\n\n".join(
            f"<file path={path!r}>\n{source}\n</file>" for path, source in artifact_sources
        )
        prompt = (
            f"{req_header}"
            f"Requirement text:\n{requirement_text}\n\n"
            "<spec.md>\n"
            f"{spec_md}\n"
            "</spec.md>\n\n"
            "<tasks.md>\n"
            f"{tasks_md or ''}\n"
            "</tasks.md>\n\n"
            "<plan.md>\n"
            f"{plan_md or ''}\n"
            "</plan.md>\n\n"
            "Artifact source to evaluate:\n"
            f"{files_blocks}\n"
        )
        return self._agent.run_sync(prompt).output


def create_implements_evaluation_agent() -> ImplementsEvaluationAgent:
    model = os.environ.get("IMPLEMENTS_AGENT_MODEL", "openai:gpt-4o-mini")
    return ImplementsEvaluationAgent(model=model)
