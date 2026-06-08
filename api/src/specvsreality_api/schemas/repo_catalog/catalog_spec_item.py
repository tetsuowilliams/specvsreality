"""Spec row in repo catalog tree."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CatalogSpecItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    paper_id: str
