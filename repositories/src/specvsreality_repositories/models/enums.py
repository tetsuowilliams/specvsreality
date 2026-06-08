"""Domain enums shared by ORM models."""

from __future__ import annotations

from enum import StrEnum


class SpecItemType(StrEnum):
    """Kind of spec item extracted from a spec bundle."""

    FUNCTIONAL_BEHAVIOR = "functional_behavior"
    INPUT_RULE = "input_rule"
    OUTPUT_RULE = "output_rule"
    ERROR_HANDLING = "error_handling"
    EDGE_CASE = "edge_case"
    EXCLUSION = "exclusion"
    NON_FUNCTIONAL_CONSTRAINT = "non_functional_constraint"
    ACCEPTANCE_SCENARIO = "acceptance_scenario"
    CONTEXT = "context"
    TASK = "task"
    DESIGN_NOTE = "design_note"


class SpecItemImportance(StrEnum):
    """How strongly a spec item should be enforced."""

    MUST = "must"
    SHOULD = "should"
    OPTIONAL = "optional"
    CONTEXT = "context"


class AgentName(StrEnum):
    """LLM agent that produced a run metric row."""

    SPEC_EXTRACTION = "spec_extraction"
    ARTIFACT_CANDIDATE = "artifact_candidate"
    IMPLEMENTS = "implements"
