"""Git commit row: a single commit observed while walking a repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class Commit(Base):
    """A commit on a tracked repository's default branch."""

    __tablename__ = "commit"
    __table_args__ = (
        UniqueConstraint("repo_id", "commit_sha", name="uq_commit_repo_sha"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("git_repo.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    commit_sha: Mapped[str] = mapped_column(String(64), nullable=False)
    commit_message: Mapped[str] = mapped_column(Text, nullable=False)
    committed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
