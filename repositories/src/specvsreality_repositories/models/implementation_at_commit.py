"""Implementation evaluation for a spec item at a commit."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class ImplementationAtCommit(Base):
    """Whether a spec item is implemented when evaluated at a given commit."""

    __tablename__ = "implementation_at_commit"
    __table_args__ = (
        UniqueConstraint(
            "spec_item_id",
            "commit_id",
            name="uq_implementation_at_commit_item_commit",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_item_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("spec_item.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    commit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("commit.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    implemented: Mapped[bool] = mapped_column(Boolean, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    gaps: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
