"""GET /repos/{repo_id}/catalog response."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from specvsreality_api.schemas.repo_catalog.catalog_spec_item import CatalogSpecItem


class RepoCatalogResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    specs: list[CatalogSpecItem]
