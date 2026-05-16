"""Structured outputs for requirement-vs-artifact implementation checks."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ImplementsAssessment(BaseModel):
    """Whether artifact source code satisfies a single requirement."""

    implements: bool = Field(
        description=(
            "True only if this artifact's code materially contributes to satisfying "
            "the requirement: behaviour, contracts, or obligations implied by the "
            "requirement are present in the shown code without relying on unseen code."
        ),
    )

    confidence: str = Field(
        description='Subjective certainty: one of "high", "medium", "low".',
    )

    reasoning: str = Field(
        min_length=1,
        description=(
            "Short explanation tying concrete symbols, functions, or control flow "
            "in the artifact to specific phrases in the requirement."
        ),
    )

    gaps: list[str] = Field(
        default_factory=list,
        description=(
            "If implements is false or confidence is not high, list concrete gaps, "
            "missing cases, or ambiguities; otherwise empty."
        ),
    )
