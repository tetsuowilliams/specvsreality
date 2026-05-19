"""One spec_version row in spec detail."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SpecDetailVersionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    spec_blob_sha: str
    plan_blob_sha: str | None = None
    tasks_blob_sha: str | None = None
    first_seen_commit: str
    first_seen_at: datetime
