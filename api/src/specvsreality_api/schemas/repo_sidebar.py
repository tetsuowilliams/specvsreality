"""Response schemas for the compact repo sidebar."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SidebarSpecVersion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version_id: int
    commit_sha: str
    commit_message: str
    committed_at: datetime
    title: str | None
    status: str


class SidebarSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
    title: str
    versions: list[SidebarSpecVersion]


class RepoSidebarResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specs: list[SidebarSpec]
