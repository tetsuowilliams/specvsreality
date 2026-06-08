"""Response schemas for the spec tree view."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SpecTreeImplementsArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    artifact_version_id: int
    filepath: str
    evidence_file: str | None
    evidence_line_number: int | None
    evidence_snippet: str | None
    evidence_relevance: str | None


class SpecTreeImplementation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    commit_sha: str
    commit_message: str
    committed_at: datetime
    implemented: bool
    summary: str | None
    gaps: list[str]
    confidence: float | None
    artifacts: list[SpecTreeImplementsArtifact]


class SpecTreeItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    local_key: str
    item_type: str
    importance: str
    text: str
    source_quote: str
    success_criteria: list[str]
    failure_criteria: list[str]
    implementations: list[SpecTreeImplementation]


class SpecTreeVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    commit_sha: str
    commit_message: str
    committed_at: datetime
    title: str | None
    summary: str | None
    spec_md: str
    tasks_md: str | None
    plan_md: str | None
    items: list[SpecTreeItem]


class SpecTreeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
    versions: list[SpecTreeVersion]
