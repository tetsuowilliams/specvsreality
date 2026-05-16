"""Full gantt chart API response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from specvsreality_api.schemas.gantt.gantt_artifact_block import GanttArtifactBlock
from specvsreality_api.schemas.gantt.gantt_chart_meta import GanttChartMeta
from specvsreality_api.schemas.gantt.gantt_requirement_block import GanttRequirementBlock


class GanttChartResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meta: GanttChartMeta
    requirement: GanttRequirementBlock
    artifacts: list[GanttArtifactBlock]
