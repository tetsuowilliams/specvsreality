"""API payload for the latest stored requirement version (by commit time)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class RequirementLatestVersionResponse(BaseModel):
    paper_id: str = Field(description="Requirement paper id under the spec.")
    requirement_text: str = Field(description="Text body from the latest requirement_version row.")
    commit_id: str
    commit_datetime: datetime
