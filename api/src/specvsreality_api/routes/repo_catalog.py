"""Repo catalog and spec tree read routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.deps.session import get_session
from specvsreality_api.facades.spec_tree_facade import SpecTreeFacade
from specvsreality_api.facades.spec_view_facade import SpecViewFacade
from specvsreality_api.schemas.repo_catalog import CatalogSpecItem, RepoCatalogResponse
from specvsreality_api.schemas.spec_tree import SpecTreeResponse
from specvsreality_api.schemas.spec_view import SpecViewMarkdownResponse, SpecViewOverviewResponse
from specvsreality_repositories.repos import create_git_repo_repo, create_spec_repo

router = APIRouter(tags=["repo-catalog"])


@router.get("/repos/{repo_id}/catalog", response_model=RepoCatalogResponse)
async def get_repo_catalog(
    repo_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> RepoCatalogResponse:
    git_repo = create_git_repo_repo(session).get_by_id(repo_id)
    if git_repo is None:
        raise HTTPException(status_code=404, detail="repo not found")

    spec_repo = create_spec_repo(session)
    specs_out = [
        CatalogSpecItem(id=spec.id, paper_id=spec.paper_id)
        for spec in spec_repo.list_for_repo(repo_id=repo_id)
    ]
    return RepoCatalogResponse(specs=specs_out)


@router.get("/repos/{repo_id}/specs/{spec_id}/tree", response_model=SpecTreeResponse)
async def get_spec_tree(
    repo_id: int,
    spec_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> SpecTreeResponse:
    return SpecTreeFacade(session).get_tree(repo_id=repo_id, spec_id=spec_id)


@router.get("/repos/{repo_id}/specs/{spec_id}/view", response_model=SpecViewOverviewResponse)
async def get_spec_view_overview(
    repo_id: int,
    spec_id: int,
    session: Annotated[Session, Depends(get_session)],
    commit_sha: str | None = None,
) -> SpecViewOverviewResponse:
    return SpecViewFacade(session).get_overview(
        repo_id=repo_id,
        spec_id=spec_id,
        commit_sha=commit_sha,
    )


@router.get(
    "/repos/{repo_id}/specs/{spec_id}/view/markdown",
    response_model=SpecViewMarkdownResponse,
)
async def get_spec_view_markdown(
    repo_id: int,
    spec_id: int,
    session: Annotated[Session, Depends(get_session)],
    commit_sha: str | None = None,
) -> SpecViewMarkdownResponse:
    return SpecViewFacade(session).get_markdown(
        repo_id=repo_id,
        spec_id=spec_id,
        commit_sha=commit_sha,
    )
