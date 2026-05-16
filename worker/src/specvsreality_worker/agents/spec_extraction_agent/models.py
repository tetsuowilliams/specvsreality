"""Structured outputs for spec extraction."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ParsedRequirement(BaseModel):
    id: str = Field(
        min_length=1,
        description=(
            "Stable requirement identifier within this specification "
            "(for example FR-001, API-002, CLI-003). "
            "Identifiers should remain stable across minor wording changes "
            "where possible."
        ),
    )

    text: str = Field(
        min_length=1,
        description=(
            "Canonical requirement text describing the expected system behaviour. "
            "This should focus on observable behaviour and business intent rather "
            "than implementation details or repository structure."
        ),
    )

    path_globs: list[str] = Field(
        default_factory=list,
        description=(
            "Non-empty when possible: repository-relative glob patterns (e.g. src/**/*.py, "
            "tests/**) likely to match implementation or tests for this requirement. "
            "Derive from the requirement text plus paths or modules mentioned in tasks/plan. "
            "Prefer a few broad patterns over an empty list. "
            "Loose discovery hints, not authoritative layout."
        ),
    )


class SpecExtractionResult(BaseModel):
    spec_title: str = Field(
        min_length=1,
        description="Human-readable specification title.",
    )

    functional_requirements: list[ParsedRequirement] = Field(
        default_factory=list,
        description="Structured requirements extracted from the specification.",
    )
