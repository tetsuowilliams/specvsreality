"""Tracked git repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, DateTime, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models._types import BigIntPk
from specvsreality_repositories.models.base import Base


class Repository(Base):
    """A repository under spec/implementation tracking."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    default_branch: Mapped[str] = mapped_column(
        Text, nullable=False, server_default="main"
    )
    clone_location: Mapped[str | None] = mapped_column(Text, nullable=True)
    cursor_position: Mapped[str | None] = mapped_column(CHAR(40), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
