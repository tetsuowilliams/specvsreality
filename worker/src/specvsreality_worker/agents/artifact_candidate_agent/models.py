"""Structured inputs and outputs for artifact candidate discovery."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpecItemContext(BaseModel):
    """Lightweight view of a spec item used to guide candidate discovery."""

    local_key: str
    item_type: str
    text: str
    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)


class CandidateArtifact(BaseModel):
    filepath: str = Field(
        min_length=1,
        description=(
            "Repository-relative path to a source file that may implement one or more of the "
            "spec items, e.g. src/pkg/count.py."
        ),
    )
    reasoning: str = Field(
        description=(
            "Why this file was selected as a candidate implementation for the spec, referencing "
            "the spec items it likely relates to."
        ),
    )


class ArtifactCandidateResult(BaseModel):
    candidates: list[CandidateArtifact] = Field(
        default_factory=list,
        description=(
            "Files from the repository snapshot that are plausible implementations of the spec. "
            "Each file should be listed at most once."
        ),
    )
