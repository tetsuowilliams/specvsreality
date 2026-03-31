"""Spec document extracted from a repository file."""

from __future__ import annotations

from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Spec(BaseModel):
    """A spec file snapshot (metadata + full text)."""

    id: UUID = Field(default_factory=uuid4)
    filename: str
    filepath: str
    content: str
