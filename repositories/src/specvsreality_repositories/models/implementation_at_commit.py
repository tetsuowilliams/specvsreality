"""Implementation evaluation for a requirement version at a commit."""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class ImplementationAtCommit(Base):
    """Whether a requirement version is implemented when evaluated at a given commit."""

    __tablename__ = "implementation_at_commit"
    __table_args__ = (
        UniqueConstraint(
            "requirement_version_id",
            "evaluation_commit_sha",
            name="uq_implementation_at_commit_rv_commit",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    requirement_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("requirement_version.id", ondelete="CASCADE"),
        nullable=False,
    )
    implemented: Mapped[bool] = mapped_column(Boolean, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    gaps: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)
