"""Response schemas for commit decision logs."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CommitLogSidebarEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commit_sha: str
    commit_message: str
    committed_at: datetime
    log_count: int


class CommitLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str
    spec_folder: str
    message: str
    reasoning: str
    created_at: datetime


class RepoLogsSidebarResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commits: list[CommitLogSidebarEntry]


class RepoCommitLogsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    commit_sha: str
    commit_message: str
    committed_at: datetime
    logs: list[CommitLogEntry]
