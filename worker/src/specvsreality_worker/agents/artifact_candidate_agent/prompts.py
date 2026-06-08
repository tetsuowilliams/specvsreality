"""Prompt templates for artifact candidate discovery."""

from __future__ import annotations

from collections.abc import Sequence

from specvsreality_worker.agents.artifact_candidate_agent.models import SpecItemContext

SYSTEM_PROMPT = (
    "You are a senior engineer identifying which files in a repository snapshot are plausible "
    "implementations of a software specification. "
    "You are given a spec (spec.md plus optional tasks.md and plan.md) and a list of structured "
    "spec items extracted from it. "
    "Use the repository tools to explore the codebase: locate relevant files, read code, "
    "and search for symbols or behaviour described by the spec items. "
    "Prefer find_files and read_file over search_text. "
    "When using read_file, request at most ~120 lines per call (start_line/end_line). "
    "When using search_text, always pass a specific file_glob (e.g. src/**/*.py); never search the "
    "whole repository without file_glob. "
    "Your goal is to return a focused list of candidate files (not requirements judgements) that a "
    "later evaluator will inspect to decide whether each spec item is implemented. "
    "Include source files that contain relevant logic; you may include tests when they directly "
    "demonstrate the behaviour. Exclude unrelated files, generated assets, and the spec files "
    "themselves. "
    "Only list files you actually located with the tools, using their exact relative paths. "
    "Do not invent file paths or contents."
)


def _format_spec_items(spec_items: Sequence[SpecItemContext]) -> str:
    if not spec_items:
        return "(no spec items extracted)"
    blocks: list[str] = []
    for item in spec_items:
        lines = [f"- [{item.local_key}] ({item.item_type}) {item.text}"]
        if item.success_criteria:
            lines.append("  success_criteria:")
            lines.extend(f"    - {criterion}" for criterion in item.success_criteria)
        if item.failure_criteria:
            lines.append("  failure_criteria:")
            lines.extend(f"    - {criterion}" for criterion in item.failure_criteria)
        blocks.append("\n".join(lines))
    return "\n".join(blocks)


def build_discovery_prompt(
    *,
    spec_md: str,
    tasks_md: str | None,
    plan_md: str | None,
    spec_items: Sequence[SpecItemContext],
) -> str:
    return (
        "Find the files in this repository snapshot that plausibly implement the spec below.\n\n"
        "Spec items to cover:\n"
        f"{_format_spec_items(spec_items)}\n\n"
        "Background spec-kit markdown:\n\n"
        "<spec.md>\n"
        f"{spec_md}\n"
        "</spec.md>\n\n"
        "<tasks.md>\n"
        f"{tasks_md or ''}\n"
        "</tasks.md>\n\n"
        "<plan.md>\n"
        f"{plan_md or ''}\n"
        "</plan.md>\n\n"
        "Explore the repository using the available tools, then return the list of candidate files "
        "with a short reasoning for each."
    )
