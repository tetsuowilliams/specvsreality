"""Requirement row with latest evaluation status for spec detail."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class SpecRequirementStatusItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
    has_version: bool = Field(description="True when at least one requirement version exists.")
    implemented: bool | None = Field(
        default=None,
        description="Latest version evaluation; null when unevaluated or no version.",
    )
