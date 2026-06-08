"""Candidate artifact proposed as potentially implementing a spec version."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class ArtifactCandidate(Base):
    """An artifact version flagged as a candidate implementation for a spec version."""

    __tablename__ = "artifact_candidate"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("spec_version.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    artifact_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("artifact_version.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    reasoning: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Why this artifact was selected as a candidate for the spec version.",
    )
