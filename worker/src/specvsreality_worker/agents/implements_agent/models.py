"""Structured inputs and outputs for batch spec-item implementation evaluation."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SpecItemForEvaluation(BaseModel):
    """A spec item handed to the evaluator, carrying its database id for round-tripping."""

    spec_item_id: int
    local_key: str
    item_type: str
    text: str
    success_criteria: list[str] = Field(default_factory=list)
    failure_criteria: list[str] = Field(default_factory=list)


class CandidateArtifactContent(BaseModel):
    """A candidate artifact and its file content provided to the evaluator."""

    filepath: str
    content: str


class ArtifactEvidence(BaseModel):
    artifact_id: str = Field(
        description=(
            "Repository-relative path of the candidate artifact that provides this evidence, "
            "matching one of the candidate filepaths provided in the prompt."
        ),
    )
    evidence_line_number: int | None = Field(
        default=None,
        description="1-based line number of the cited snippet within the artifact, when known.",
    )
    evidence_snippet: str = Field(
        description="Short excerpt of the code that supports the implementation claim.",
    )
    evidence_relevance: str = Field(
        description="How this code satisfies part of the spec item.",
    )


class SpecItemEvaluation(BaseModel):
    spec_item_id: int = Field(
        description="The spec_item_id of the spec item being evaluated, copied from the input.",
    )
    summary: str = Field(
        description="Brief overall assessment of how the spec item is or is not met.",
    )
    implemented: bool = Field(
        description=(
            "True only if the candidate artifacts materially satisfy the spec item based on "
            "the inspected code."
        ),
    )
    gaps: list[str] = Field(
        default_factory=list,
        description=(
            "Missing behaviour, unverified assumptions, or ambiguities when implemented is false "
            "or confidence is low; otherwise empty."
        ),
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Subjective certainty between 0.0 and 1.0.",
    )
    implemented_by: list[ArtifactEvidence] = Field(
        default_factory=list,
        description="Concrete code citations from the candidate artifacts for the assessment.",
    )


class ImplementsBatchResult(BaseModel):
    evaluations: list[SpecItemEvaluation] = Field(
        default_factory=list,
        description="One evaluation per spec item provided in the input batch.",
    )
