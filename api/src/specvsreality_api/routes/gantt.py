"""Gantt chart API for requirements and implementing artifacts."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from specvsreality_api.facades.gantt_chart_facade import GanttChartFacade, get_gantt_chart_facade
from specvsreality_api.schemas.gantt import GanttChartResponse
from specvsreality_api.schemas.requirement_latest_version import RequirementLatestVersionResponse

router = APIRouter(tags=["gantt"])


@router.get(
    "/repos/{repo_id}/specs/{spec_id}/requirements/latest-version",
    response_model=RequirementLatestVersionResponse,
)
async def get_requirement_latest_version(
    repo_id: int,
    spec_id: int,
    facade: Annotated[GanttChartFacade, Depends(get_gantt_chart_facade)],
    requirement_id: Annotated[
        int | None,
        Query(
            description=(
                "Requirement row id; required when the spec has more than one requirement."
            ),
        ),
    ] = None,
) -> RequirementLatestVersionResponse:
    return facade.get_requirement_latest_version(repo_id, spec_id, requirement_id=requirement_id)


@router.get(
    "/repos/{repo_id}/specs/{spec_id}/gantt",
    response_model=GanttChartResponse,
)
async def get_spec_gantt_chart(
    repo_id: int,
    spec_id: int,
    facade: Annotated[GanttChartFacade, Depends(get_gantt_chart_facade)],
    requirement_id: Annotated[
        int | None,
        Query(
            description=(
                "Requirement row id; required when the spec has more than one requirement."
            ),
        ),
    ] = None,
) -> GanttChartResponse:
    return facade.get_chart(repo_id=repo_id, spec_id=spec_id, requirement_id=requirement_id)
