"""Global LLM usage metrics dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from specvsreality_api.deps.session import get_session
from specvsreality_api.facades.metrics_dashboard_facade import MetricsDashboardFacade
from specvsreality_api.schemas.metrics_dashboard import MetricsDashboardResponse

router = APIRouter(tags=["metrics"])


@router.get("/metrics", response_model=MetricsDashboardResponse)
async def get_metrics_dashboard(
    session: Annotated[Session, Depends(get_session)],
    repo_id: Annotated[int | None, Query()] = None,
    recent_limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> MetricsDashboardResponse:
    return MetricsDashboardFacade(session).get_dashboard(
        repo_id=repo_id,
        recent_limit=recent_limit,
    )
