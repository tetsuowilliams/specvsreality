"""Structured outputs for spec extraction."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

SpecItemTypeLiteral = Literal[
    "functional_behavior",
    "input_rule",
    "output_rule",
    "error_handling",
    "edge_case",
    "exclusion",
    "non_functional_constraint",
    "acceptance_scenario",
    "context",
    "task",
    "design_note",
]

SpecItemImportanceLiteral = Literal[
    "must",
    "should",
    "optional",
    "context",
]


class ExtractedSpecItem(BaseModel):
    local_key: str = Field(
        min_length=1,
        description=(
            "Identifier for this item within this spec version. "
            "Use an explicit id from the spec if present, such as FR-003, AC-002, US-001. "
            "If no explicit id exists, generate a stable local id such as OBL-001. "
            "This key only needs to be unique within this extracted spec version."
        ),
    )
    item_type: SpecItemTypeLiteral = Field(
        description=(
            "The kind of spec item. Use functional_behavior, input_rule, output_rule, "
            "error_handling, edge_case, exclusion, non_functional_constraint, or "
            "acceptance_scenario for items that describe code-verifiable behaviour. "
            "Use context, task, or design_note for material that should usually not be "
            "evaluated directly."
        ),
    )
    text: str = Field(
        min_length=1,
        description=(
            "The original or near-original text of the item as extracted from the spec bundle. "
            "Keep this close to the source wording so it can be shown in the UI."
        ),
    )
    source_quote: str = Field(
        min_length=1,
        description=(
            "Short exact quote or close excerpt from the source document that supports this item. "
            "Used for UI highlighting/debugging."
        ),
    )
    importance: SpecItemImportanceLiteral = Field(
        description=(
            "How strongly this item must be enforced. Use must for hard obligations, "
            "should for strong recommendations, optional for nice-to-haves, and context "
            "for background material that is not directly verifiable."
        ),
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description=(
            "Concrete evidence that would indicate this item is satisfied. "
            "These should be useful to the implementation evaluator. "
            "Example: 'CLI parser defines one positional directory argument'."
        ),
    )
    failure_criteria: list[str] = Field(
        default_factory=list,
        description=(
            "Concrete evidence that would indicate this item is not satisfied or is wrong. "
            "Example: 'The tool hard-codes the directory path instead of accepting user input'."
        ),
    )


class ExtractedSpec(BaseModel):
    title: str = Field(
        min_length=1,
        description="Human-readable title for this spec version.",
    )
    summary: str = Field(
        description=(
            "Short summary of what this spec is trying to achieve. "
            "This is for UI/debugging and should not replace item-level evaluation."
        ),
    )
    items: list[ExtractedSpecItem] = Field(
        default_factory=list,
        description=(
            "Implementation-verifiable obligations and other structured spec items extracted "
            "from the spec bundle."
        ),
    )
