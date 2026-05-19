"""Spec-kit specification (logical identity by repository + name)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models._types import BigIntPk
from specvsreality_repositories.models.base import Base


class Spec(Base):
    """A spec-kit spec discovered from the tree (e.g. specs/<name>/)."""

    __tablename__ = "specs"
    __table_args__ = (
        UniqueConstraint("repository_id", "name", name="uq_specs_repo_name"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    spec_path: Mapped[str] = mapped_column(Text, nullable=False)
    plan_path: Mapped[str] = mapped_column(Text, nullable=False)
    tasks_path: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
