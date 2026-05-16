"""One spec_version row in spec detail."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SpecDetailVersionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    spec_md: str
    tasks_md: str | None
    plan_md: str | None
