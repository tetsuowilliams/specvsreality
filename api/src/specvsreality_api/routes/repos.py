"""List and create tracked repositories."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from specvsreality_api.config import Settings, get_settings
from specvsreality_api.deps.session import get_session
from specvsreality_api.messaging.publisher import MessagePublisher, PikaMessagePublisher
from specvsreality_messages import ScanRepoMessage
from specvsreality_repositories.repos import RepositoryRepo

router = APIRouter(tags=["repos"])


class RepoListItem(BaseModel):
    id: int
    name: str
    url: str
    default_branch: str
    cursor_position: str | None = None
    clone_location: str | None = None


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
    rows = RepositoryRepo(session).list_all()
    return [_to_item(row) for row in rows]


@router.post("/repos", response_model=CreateRepoResponse)
async def post_repos(
    body: CreateRepoRequest,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    publisher: Annotated[MessagePublisher, Depends(get_publisher)],
) -> CreateRepoResponse:
    repo = RepositoryRepo(session).add(name=body.name, url=body.url)
    session.commit()
    message = ScanRepoMessage(repo_id=str(repo.id))
    await publisher.publish(message.model_dump_json().encode("utf-8"), settings)
    return CreateRepoResponse(repo=_to_item(repo))


@router.get("/repos/{repo_id}", response_model=RepoListItem)
async def get_repo(
    repo_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> RepoListItem:
    row = RepositoryRepo(session).get_by_id(repo_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"repo not found: {repo_id}")
    return _to_item(row)
