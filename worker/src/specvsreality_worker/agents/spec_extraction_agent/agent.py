from __future__ import annotations

import os

import opik
from pydantic_ai import Agent

from specvsreality_worker.agents.pydantic_ai_verbose import build_event_stream_handler
from specvsreality_worker.agents.spec_extraction_agent.models import SpecExtractionResult
_OPIK_PROJECT = "specvsreality-worker"


class SpecExtractionAgent:
    def __init__(self, model: str) -> None:
        self._agent = Agent(
            model=model,
            output_type=SpecExtractionResult,
            system_prompt=(
                "Extract structured software specification information from markdown files. "
                "Return a concise title, all functional requirements, and user acceptance scenarios. "
                "For each functional requirement, preserve stable requirement IDs when present. "
                "Each functional requirement must include path_globs: repository-relative glob "
                "patterns (for example src/**/*.py, tests/**/*, frontend/src/**) that plausibly "
                "cover implementation or tests for that requirement. Infer globs from the "
                "requirement wording and from any file paths, components, or modules named in "
                "tasks.md or plan.md; when unsure, propose a few broad patterns rather than leaving "
                "path_globs empty."
            ),
        )

    @opik.track(
        name="spec-extraction-agent",
        project_name=_OPIK_PROJECT,
        tags=["agent:spec-extraction"],
        ignore_arguments=( "tasks_md", "plan_md"),
    )
    def extract_spec(
        self,
        *,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
    ) -> SpecExtractionResult:
        prompt = (
            "Analyze the following spec-kit markdown files and extract:\n"
            "1) spec_title\n"
            "2) functional_requirements: for each item provide id, text (requirement body), "
            "and path_globs (non-empty list of repo-relative globs as discovery hints, "
            "e.g. **/*.py or src/pkg/**)\n"
            "3) user_acceptance_scenarios: list of concise scenario statements\n\n"
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
        return self._agent.run_sync(
            prompt,
            event_stream_handler=build_event_stream_handler(),
        ).output


def create_spec_extraction_agent() -> SpecExtractionAgent:
    model = os.environ.get("SPEC_EXTRACTION_MODEL", "openai:gpt-4o-mini")
    return SpecExtractionAgent(model=model)
