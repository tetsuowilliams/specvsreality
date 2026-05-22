"""Links a requirement version to an artifact version."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class Implements(Base):
    """Many-to-many: which artifact versions implement a requirement version."""

    __tablename__ = "implements"

    implementation_at_commit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("implementation_at_commit.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("artifact_version.id", ondelete="CASCADE"),
        primary_key=True,
    )
    evidence_file: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    evidence_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_relevance: Mapped[str | None] = mapped_column(Text, nullable=True)
