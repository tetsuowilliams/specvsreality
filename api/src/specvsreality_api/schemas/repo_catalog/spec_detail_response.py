"""GET /repos/{repo_id}/specs/{spec_id} response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from specvsreality_api.schemas.repo_catalog.spec_detail_version_item import SpecDetailVersionItem
from specvsreality_api.schemas.repo_catalog.spec_requirement_status_item import (
    SpecRequirementStatusItem,
)


class SpecDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
    versions: list[SpecDetailVersionItem]
    requirements: list[SpecRequirementStatusItem] = Field(
        default_factory=list,
        description="All requirements for this spec with latest implementation status.",
    )
