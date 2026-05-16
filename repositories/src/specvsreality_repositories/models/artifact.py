"""Artifact path identity (file in the repo)."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class Artifact(Base):
    """A file artifact tracked by path."""

    __tablename__ = "artifact"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filepath: Mapped[str] = mapped_column(String(4096), nullable=False)
