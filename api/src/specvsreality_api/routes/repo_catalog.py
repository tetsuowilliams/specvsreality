"""Repo catalog and spec detail read routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.deps.session import get_session
from specvsreality_api.schemas.repo_catalog import (
    CatalogRequirementItem,
    CatalogSpecItem,
    RepoCatalogResponse,
    SpecDetailResponse,
    SpecDetailVersionItem,
    SpecRequirementStatusItem,
)
from specvsreality_repositories.repos import (
    create_git_repo_repo,
    create_requirement_repo,
    create_requirement_version_repo,
    create_spec_repo,
    create_spec_version_repo,
)

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
    requirement_repo = create_requirement_repo(session)
    specs_out: list[CatalogSpecItem] = []
    for spec in spec_repo.list_for_repo(repo_id=repo_id):
        reqs = [
            CatalogRequirementItem(id=r.id, paper_id=r.paper_id)
            for r in requirement_repo.list_for_spec(spec_id=spec.id)
        ]
        specs_out.append(CatalogSpecItem(id=spec.id, paper_id=spec.paper_id, requirements=reqs))
    return RepoCatalogResponse(specs=specs_out)


@router.get("/repos/{repo_id}/specs/{spec_id}", response_model=SpecDetailResponse)
async def get_repo_spec_detail(
    repo_id: int,
    spec_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> SpecDetailResponse:
    spec_repo = create_spec_repo(session)
    spec = spec_repo.get_by_id(spec_id)
    if spec is None or spec.repo_id != repo_id:
        raise HTTPException(status_code=404, detail="spec not found")

    versions = create_spec_version_repo(session).list_for_spec_ordered(spec_id=spec_id)
    requirements = create_requirement_repo(session).list_for_spec(spec_id=spec_id)
    latest_by_req = {
        rv.requirement_id: rv
        for rv in create_requirement_version_repo(session).list_latest(spec_id=spec_id)
    }
    requirement_status = [
        SpecRequirementStatusItem(
            id=r.id,
            paper_id=r.paper_id,
            has_version=r.id in latest_by_req,
            implemented=latest_by_req[r.id].implemented if r.id in latest_by_req else None,
        )
        for r in requirements
    ]
    return SpecDetailResponse(
        id=spec.id,
        paper_id=spec.paper_id,
        versions=[
            SpecDetailVersionItem(
                id=v.id,
                spec_md=v.spec_md,
                tasks_md=v.tasks_md,
                plan_md=v.plan_md,
            )
            for v in versions
        ],
        requirements=requirement_status,
    )
