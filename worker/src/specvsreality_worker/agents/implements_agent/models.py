"""Structured outputs for requirement implementation checks."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CodeEvidence(BaseModel):
    file: str = Field(
        description="Repository-relative path to the file containing the cited code.",
    )
    line_number: int | None = Field(
        default=None,
        description="1-based line number of the cited snippet, when known.",
    )
    snippet: str = Field(
        description="Short excerpt of the code that supports the implementation claim.",
    )
    relevance: str = Field(
        description="How this code satisfies part of the requirement.",
    )


class RequirementJustification(BaseModel):
    requirement: str = Field(
        description="The requirement text that was evaluated.",
    )
    implemented: bool = Field(
        description=(
            "True only if the codebase materially satisfies the requirement based on "
            "inspected code."
        ),
    )
    confidence: str = Field(
        description='Subjective certainty: one of "high", "medium", "low".',
    )
    summary: str = Field(
        description="Brief overall assessment of how the requirement is or is not met.",
    )
    evidence: list[CodeEvidence] = Field(
        default_factory=list,
        description="Concrete code citations supporting the assessment.",
    )
    gaps: list[str] = Field(
        default_factory=list,
        description=(
            "Missing behaviour, unverified assumptions, or ambiguities when implemented is "
            "false or confidence is not high; otherwise empty."
        ),
    )
