"""Single gantt history interval."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GanttHistorySegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: datetime
    end: datetime
    status: str
    commit: str | None = Field(
        default=None,
        description=(
            "Git commit SHA anchoring this segment: spec-version first_seen_commit "
            "for requirements, or the commit where the artifact path was observed."
        ),
    )
    requirement_text: str | None = Field(
        default=None,
        description="Requirement body for requirement-row segments; null for artifacts.",
    )
    blob_sha: str | None = Field(
        default=None,
        description="Content blob SHA for artifact-row segments; null for requirements.",
    )
