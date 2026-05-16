"""Requirement row in repo catalog tree."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CatalogRequirementItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
