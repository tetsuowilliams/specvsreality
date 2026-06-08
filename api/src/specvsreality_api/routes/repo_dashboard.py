"""Repository dashboard and sidebar routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from specvsreality_api.deps.session import get_session
from specvsreality_api.facades.repo_dashboard_facade import RepoDashboardFacade
from specvsreality_api.facades.repo_sidebar_facade import RepoSidebarFacade
from specvsreality_api.schemas.repo_dashboard import RepoDashboardResponse
from specvsreality_api.schemas.repo_sidebar import RepoSidebarResponse

router = APIRouter(tags=["repo-dashboard"])


@router.get("/repos/{repo_id}/dashboard", response_model=RepoDashboardResponse)
async def get_repo_dashboard(
    repo_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> RepoDashboardResponse:
    return RepoDashboardFacade(session).get_dashboard(repo_id=repo_id)


@router.get("/repos/{repo_id}/sidebar", response_model=RepoSidebarResponse)
async def get_repo_sidebar(
    repo_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> RepoSidebarResponse:
    return RepoSidebarFacade(session).get_sidebar(repo_id=repo_id)
