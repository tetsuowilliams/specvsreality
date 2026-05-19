"""Repo catalog and spec detail read routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import asc, select
from sqlalchemy.orm import Session

from specvsreality_api.deps.session import get_session
from specvsreality_api.schemas.repo_catalog import (
    CatalogRequirementItem,
    CatalogSpecItem,
    RepoCatalogResponse,
    SpecDetailResponse,
    SpecDetailVersionItem,
)
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos import (
    RepositoryRepo,
    RequirementRepo,
    SpecRepo,
)

router = APIRouter(tags=["repo-catalog"])


@router.get("/repos/{repo_id}/catalog", response_model=RepoCatalogResponse)
async def get_repo_catalog(
    repo_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> RepoCatalogResponse:
    repository = RepositoryRepo(session).get_by_id(repo_id)
    if repository is None:
        raise HTTPException(status_code=404, detail="repo not found")

    spec_repo = SpecRepo(session)
    requirement_repo = RequirementRepo(session)
    specs_out: list[CatalogSpecItem] = []
    for spec in spec_repo.list_for_repo(repository_id=repo_id):
        reqs = [
            CatalogRequirementItem(id=r.id, paper_id=r.external_id)
            for r in requirement_repo.list_for_spec(spec_id=spec.id)
        ]
        specs_out.append(
            CatalogSpecItem(id=spec.id, paper_id=spec.name, requirements=reqs)
        )
    return RepoCatalogResponse(specs=specs_out)


@router.get("/repos/{repo_id}/specs/{spec_id}", response_model=SpecDetailResponse)
async def get_repo_spec_detail(
    repo_id: int,
    spec_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> SpecDetailResponse:
    spec_repo = SpecRepo(session)
    spec = spec_repo.get_by_id(spec_id)
    if spec is None or spec.repository_id != repo_id:
        raise HTTPException(status_code=404, detail="spec not found")

    stmt = (
        select(SpecVersion)
        .where(SpecVersion.spec_id == spec_id)
        .order_by(asc(SpecVersion.first_seen_at), asc(SpecVersion.id))
    )
    versions = list(session.scalars(stmt).all())

    return SpecDetailResponse(
        id=spec.id,
        paper_id=spec.name,
        versions=[
            SpecDetailVersionItem(
                id=v.id,
                spec_blob_sha=v.spec_blob_sha,
                plan_blob_sha=v.plan_blob_sha,
                tasks_blob_sha=v.tasks_blob_sha,
                first_seen_commit=v.first_seen_commit,
                first_seen_at=v.first_seen_at,
            )
            for v in versions
        ],
    )
