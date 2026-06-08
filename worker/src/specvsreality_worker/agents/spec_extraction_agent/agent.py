from __future__ import annotations

from typing import TYPE_CHECKING

import opik
from pydantic_ai import Agent

from specvsreality_repositories.models.enums import AgentName
from specvsreality_worker.agents.pydantic_ai_verbose import build_event_stream_handler
from specvsreality_worker.agents.spec_extraction_agent.models import ExtractedSpec
from specvsreality_worker.config import WorkerSettings

if TYPE_CHECKING:
    from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder

_OPIK_PROJECT = "specvsreality-worker"

_SYSTEM_PROMPT = (
    "You extract structured, implementation-verifiable spec items from spec-kit markdown "
    "(spec.md plus optional tasks.md and plan.md). "
    "Break the specification into discrete items, each capturing a single obligation, rule, "
    "scenario, or piece of context. "
    "Classify every item with an item_type and an importance. "
    "Use functional_behavior, input_rule, output_rule, error_handling, edge_case, exclusion, "
    "non_functional_constraint, and acceptance_scenario for things that can be verified against "
    "code; use context, task, and design_note for background material. "
    "For each item, populate success_criteria and failure_criteria with concrete, observable "
    "evidence that a code reviewer could check, so they can be handed to an implementation "
    "evaluator. "
    "Preserve explicit identifiers from the spec as local_key when present; otherwise generate a "
    "stable local id (e.g. OBL-001). "
    "Keep the item text close to the source wording and include a short source_quote per item. "
    "Do not invent requirements that are not supported by the source documents."
)


class SpecExtractionAgent:
    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._agent = Agent(
            model=settings.spec_extraction_model,
            output_type=ExtractedSpec,
            system_prompt=_SYSTEM_PROMPT,
        )

    @opik.track(
        name="spec-extraction-agent",
        project_name=_OPIK_PROJECT,
        tags=["agent:spec-extraction"],
        ignore_arguments=("tasks_md", "plan_md"),
    )
    def extract_spec(
        self,
        *,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        metrics: AgentMetricsRecorder | None = None,
    ) -> ExtractedSpec:
        prompt = (
            "Analyze the following spec-kit markdown files and extract a structured spec.\n"
            "Return:\n"
            "1) title: a concise human-readable title for this spec version\n"
            "2) summary: a short description of what the spec is trying to achieve\n"
            "3) items: a list of discrete spec items. For each item provide local_key, item_type, "
            "text, source_quote, importance, success_criteria, and failure_criteria.\n"
            "Focus success_criteria and failure_criteria on observable evidence.\n\n"
            "<spec.md>\n"
            f"{spec_md}\n"
            "</spec.md>\n\n"
            "<tasks.md>\n"
            f"{tasks_md or ''}\n"
            "</tasks.md>\n\n"
            "<plan.md>\n"
            f"{plan_md or ''}\n"
            "</plan.md>\n"
        )
        result = self._agent.run_sync(
            prompt,
            event_stream_handler=build_event_stream_handler(self._settings),
        )
        if metrics is not None:
            metrics.record(
                agent=AgentName.SPEC_EXTRACTION,
                model=self._settings.spec_extraction_model,
                usage=result.usage(),
                ran_at=result.timestamp(),
            )
        return result.output


def create_spec_extraction_agent(settings: WorkerSettings) -> SpecExtractionAgent:
    return SpecExtractionAgent(settings)
