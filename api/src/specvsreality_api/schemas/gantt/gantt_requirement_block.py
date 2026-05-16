"""Requirement row for gantt response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from specvsreality_api.schemas.gantt.gantt_history_segment import GanttHistorySegment


class GanttRequirementBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    history: list[GanttHistorySegment]
