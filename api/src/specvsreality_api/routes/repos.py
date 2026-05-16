"""List and create tracked git repositories."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_api.config import Settings, get_settings
from specvsreality_api.deps.session import get_session
from specvsreality_api.messaging.publisher import MessagePublisher, PikaMessagePublisher
from specvsreality_messages import ScanRepoMessage
from specvsreality_repositories.models.git_repo import GitRepo
from specvsreality_repositories.repos import GitRepoRepo

router = APIRouter(tags=["repos"])


class RepoListItem(BaseModel):
    id: int
    name: str
    url: str
    cursor_position: str
    location: str


class CreateRepoRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    url: str = Field(min_length=1, max_length=2048)


class CreateRepoResponse(BaseModel):
    queued: bool = True
    repo: RepoListItem


def get_publisher() -> MessagePublisher:
    return PikaMessagePublisher()


def _to_item(repo: object) -> RepoListItem:
    return RepoListItem.model_validate(repo, from_attributes=True)


@router.get("/repos", response_model=list[RepoListItem])
async def get_repos(
    session: Annotated[Session, Depends(get_session)],
) -> list[RepoListItem]:
    stmt = select(GitRepo).order_by(GitRepo.name.asc(), GitRepo.id.asc())
    rows = list(session.execute(stmt).scalars().all())
    return [_to_item(row) for row in rows]


@router.post("/repos", response_model=CreateRepoResponse)
async def post_repos(
    body: CreateRepoRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    publisher: Annotated[MessagePublisher, Depends(get_publisher)],
) -> CreateRepoResponse:
    repo = GitRepoRepo(session).add(name=body.name, url=body.url)
    session.commit()
    message = ScanRepoMessage(repo_id=str(repo.id))
    await publisher.publish(message.model_dump_json().encode("utf-8"), settings)
    return CreateRepoResponse(repo=_to_item(repo))


@router.get("/repos/{repo_id}", response_model=RepoListItem)
async def get_repo(
    repo_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> RepoListItem:
    row = GitRepoRepo(session).get_by_id(repo_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"repo not found: {repo_id}")
    return _to_item(row)
