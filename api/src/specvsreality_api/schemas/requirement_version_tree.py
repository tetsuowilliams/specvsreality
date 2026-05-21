"""Requirement version tree: versions and linked artifact versions with evidence."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ImplementsEvidenceItem(BaseModel):
    evidence_file: str | None = None
    evidence_line_number: int | None = None
    evidence_snippet: str | None = None
    evidence_relevance: str | None = None


class RequirementTreeArtifactVersion(BaseModel):
    artifact_version_id: int
    filepath: str
    commit_sha: str
    commit_datetime: datetime
    status: str
    file_content: str = Field(description="Snapshot content at this commit.")
    evidence: ImplementsEvidenceItem


class RequirementTreeVersion(BaseModel):
    id: int
    commit_sha: str
    commit_datetime: datetime
    requirement_text: str
    filepath_globs: list[str]
    status: str
    implemented: bool | None = None
    summary: str | None = None
    gaps: list[str] | None = None
    artifact_versions: list[RequirementTreeArtifactVersion] = Field(
        default_factory=list,
        description="Artifact versions linked via implements for this requirement version.",
    )


class RequirementVersionTreeResponse(BaseModel):
    paper_id: str = Field(description="Requirement paper id under the spec.")
    versions: list[RequirementTreeVersion] = Field(
        description="All requirement versions, newest commit first.",
    )
