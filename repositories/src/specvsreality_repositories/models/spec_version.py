"""Versioned markdown bodies for a spec."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class SpecVersion(Base):
    """Snapshot of spec.md and optional tasks.md / plan.md for a spec."""

    __tablename__ = "spec_version"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("spec.id", ondelete="CASCADE"),
        nullable=False,
    )
    spec_md: Mapped[str] = mapped_column(Text, nullable=False)
    tasks_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    plan_md: Mapped[str | None] = mapped_column(Text, nullable=True)
