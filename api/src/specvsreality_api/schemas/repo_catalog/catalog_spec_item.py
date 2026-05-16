"""Spec row in repo catalog tree."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from specvsreality_api.schemas.repo_catalog.catalog_requirement_item import CatalogRequirementItem


class CatalogSpecItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
    requirements: list[CatalogRequirementItem]
