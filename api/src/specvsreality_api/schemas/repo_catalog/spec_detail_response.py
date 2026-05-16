"""GET /repos/{repo_id}/specs/{spec_id} response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from specvsreality_api.schemas.repo_catalog.spec_detail_version_item import SpecDetailVersionItem


class SpecDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
    versions: list[SpecDetailVersionItem]
