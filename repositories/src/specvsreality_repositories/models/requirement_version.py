"""Requirement state at a given commit."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class RequirementVersion(Base):
    """Versioned requirement text and scope for a commit."""

    __tablename__ = "requirement_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("requirement.id", ondelete="CASCADE"),
        nullable=False,
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requirement_text: Mapped[str] = mapped_column(Text, nullable=False)
    filepath_globs: Mapped[list[str]] = mapped_column(ARRAY(String), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
