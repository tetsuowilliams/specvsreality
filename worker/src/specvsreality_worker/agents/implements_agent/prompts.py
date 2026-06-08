"""Prompt templates for batch spec-item implementation evaluation."""

from __future__ import annotations

from collections.abc import Sequence

from specvsreality_worker.agents.implements_agent.models import (
    CandidateArtifactContent,
    SpecItemForEvaluation,
)

SYSTEM_PROMPT = (
    "You are a senior engineer judging whether specific spec items are implemented by a set of "
    "candidate code artifacts. "
    "You are given the spec bundle (spec.md plus optional tasks.md and plan.md) for context, "
    "a list of spec items to evaluate, and the full contents of the candidate artifacts. "
    "Evaluate ONLY the spec items provided. For each one, decide whether the candidate artifacts "
    "materially satisfy it, using its success_criteria and failure_criteria as the rubric. "
    "Base your judgment only on the candidate artifact contents shown to you; do not assume the "
    "existence of code you cannot see. "
    "Cite concrete evidence: for each spec item, list the artifacts (by their exact filepath) "
    "that implement it, with a line number when known, a short snippet, and why it is relevant. "
    "Set confidence as a float between 0.0 and 1.0. When implemented is false or confidence is "
    "low, explain what is missing in gaps. "
    "Return exactly one evaluation per input spec item, echoing back its spec_item_id unchanged. "
    "Do not invent file paths, snippets, or evidence."
)


def _format_spec_items(spec_items: Sequence[SpecItemForEvaluation]) -> str:
    blocks: list[str] = []
    for item in spec_items:
        lines = [
            f"spec_item_id: {item.spec_item_id}",
            f"local_key: {item.local_key}",
            f"item_type: {item.item_type}",
            f"text: {item.text}",
        ]
        if item.success_criteria:
            lines.append("success_criteria:")
            lines.extend(f"  - {criterion}" for criterion in item.success_criteria)
        if item.failure_criteria:
            lines.append("failure_criteria:")
            lines.extend(f"  - {criterion}" for criterion in item.failure_criteria)
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def _format_candidates(candidates: Sequence[CandidateArtifactContent]) -> str:
    if not candidates:
        return "(no candidate artifacts were found for this spec)"
    blocks: list[str] = []
    for candidate in candidates:
        blocks.append(
            f"<artifact path=\"{candidate.filepath}\">\n{candidate.content}\n</artifact>"
        )
    return "\n\n".join(blocks)


def build_batch_prompt(
    *,
    spec_items: Sequence[SpecItemForEvaluation],
    candidates: Sequence[CandidateArtifactContent],
    spec_md: str,
    tasks_md: str | None,
    plan_md: str | None,
) -> str:
    return (
        "Evaluate whether each of the following spec items is implemented by the candidate "
        "artifacts.\n\n"
        "Spec items to evaluate:\n"
        f"{_format_spec_items(spec_items)}\n\n"
        "Candidate artifacts (full contents):\n"
        f"{_format_candidates(candidates)}\n\n"
        "Background spec-kit markdown (context only):\n\n"
        "<spec.md>\n"
        f"{spec_md}\n"
        "</spec.md>\n\n"
        "<tasks.md>\n"
        f"{tasks_md or ''}\n"
        "</tasks.md>\n\n"
        "<plan.md>\n"
        f"{plan_md or ''}\n"
        "</plan.md>\n\n"
        "Return one evaluation per spec item, echoing each spec_item_id."
    )
