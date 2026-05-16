"""Spec row: ties a paper to a tracked repository."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class Spec(Base):
    """Logical specification for a repo and paper."""

    __tablename__ = "spec"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("git_repo.id", ondelete="CASCADE"),
        nullable=False,
    )
