"""Repository commit decision log routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from specvsreality_api.deps.session import get_session
from specvsreality_api.facades.repo_logs_facade import RepoLogsFacade
from specvsreality_api.schemas.repo_logs import RepoCommitLogsResponse, RepoLogsSidebarResponse

router = APIRouter(tags=["repo-logs"])


@router.get("/repos/{repo_id}/logs/sidebar", response_model=RepoLogsSidebarResponse)
async def get_repo_logs_sidebar(
    repo_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> RepoLogsSidebarResponse:
    return RepoLogsFacade(session).get_sidebar(repo_id=repo_id)


@router.get("/repos/{repo_id}/logs", response_model=RepoCommitLogsResponse)
async def get_repo_commit_logs(
    repo_id: int,
    session: Annotated[Session, Depends(get_session)],
    commit_sha: Annotated[str, Query(min_length=1)],
) -> RepoCommitLogsResponse:
    return RepoLogsFacade(session).get_commit_logs(
        repo_id=repo_id,
        commit_sha=commit_sha,
    )
