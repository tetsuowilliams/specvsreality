"""Requirement row under a spec."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class Requirement(Base):
    """A requirement belonging to a spec and paper."""

    __tablename__ = "requirement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("spec.id", ondelete="CASCADE"),
        nullable=False,
    )
    paper_id: Mapped[str] = mapped_column(String(255), nullable=False)
