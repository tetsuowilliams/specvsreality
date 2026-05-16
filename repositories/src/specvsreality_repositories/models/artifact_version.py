"""Artifact snapshot at a commit."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class ArtifactVersion(Base):
    """Versioned file content for an artifact at a commit."""

    __tablename__ = "artifact_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artifact_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("artifact.id", ondelete="CASCADE"),
        nullable=False,
    )
    commit_id: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    file_content: Mapped[str] = mapped_column(Text, nullable=False)
