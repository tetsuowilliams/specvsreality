"""Top-level metadata for gantt chart response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GanttChartMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")

    requirement_implemented: bool = Field(
        description="True when the latest requirement history segment is implemented.",
    )
