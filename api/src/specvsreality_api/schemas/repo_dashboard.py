"""Response schemas for the repository dashboard."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DashboardSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specs_tracked: int
    latest_commit_sha: str | None
    latest_commit_message: str | None
    latest_commit_at: datetime | None
    coverage_percent: float | None
    missing_items: int
    low_confidence_items: int
    candidate_artifacts: int


class DashboardSpecRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_id: int
    paper_id: str
    latest_version_id: int
    latest_commit_sha: str
    status: str
    satisfied: int
    missing: int
    low_confidence: int
    candidate_artifacts: int
    last_evaluated_commit_sha: str | None
    last_evaluated_at: datetime | None


class DashboardAttentionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_id: int
    paper_id: str
    headline: str
    detail: str
    severity: str


class DashboardRecentChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec_id: int
    paper_id: str
    local_key: str | None
    message: str
    commit_sha: str
    committed_at: datetime


class DashboardArtifactActivity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filepath: str
    link_type: str
    item_count: int
    spec_paper_id: str | None
    label: str


class RepoDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_id: int
    repo_name: str
    summary: DashboardSummary
    specs: list[DashboardSpecRow]
    needs_attention: list[DashboardAttentionItem]
    recent_changes: list[DashboardRecentChange]
    artifact_activity: list[DashboardArtifactActivity]
