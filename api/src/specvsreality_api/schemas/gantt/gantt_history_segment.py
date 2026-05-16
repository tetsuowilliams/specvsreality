"""Single gantt history interval."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GanttHistorySegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: datetime
    end: datetime
    status: str
    commit: str | None = Field(default=None, description="Git commit SHA for artifact segments; null for requirement.")
