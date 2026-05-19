"""Commit -> parent edge in the git DAG."""

from __future__ import annotations

from sqlalchemy import CHAR, ForeignKey, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class CommitParent(Base):
    """One parent edge of a commit, ordered for merges."""

    __tablename__ = "commit_parents"

    commit_sha: Mapped[str] = mapped_column(
        CHAR(40),
        ForeignKey("commits.sha", ondelete="CASCADE"),
        primary_key=True,
    )
    parent_sha: Mapped[str] = mapped_column(
        CHAR(40),
        ForeignKey("commits.sha", ondelete="CASCADE"),
        primary_key=True,
    )
    parent_order: Mapped[int] = mapped_column(SmallInteger, nullable=False)
