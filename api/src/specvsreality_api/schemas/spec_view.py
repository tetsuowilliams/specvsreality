"""Response schemas for the spec markdown view."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from specvsreality_api.schemas.spec_tree import SpecTreeImplementation


class SpecViewItemSpan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: int
    end: int


class SpecViewItemSpans(BaseModel):
    model_config = ConfigDict(extra="forbid")

    spec: SpecViewItemSpan | None = None
    tasks: SpecViewItemSpan | None = None
    plan: SpecViewItemSpan | None = None


class SpecViewItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    local_key: str
    item_type: str
    importance: str
    text: str
    source_quote: str
    spans: SpecViewItemSpans
    success_criteria: list[str]
    failure_criteria: list[str]
    implementations: list[SpecTreeImplementation]


class SpecViewVersion(BaseModel):
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


class SpecViewSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_items: int
    tracked_items: int
    evaluated: int
    implemented: int
    mandatory_gaps: int
    low_confidence: int
    unevaluated: int
    coverage_percent: float | None
    status: str


class SpecViewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
    version: SpecViewVersion
    summary: SpecViewSummary
    items: list[SpecViewItem]
