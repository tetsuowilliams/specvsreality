"""Git commit record."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CHAR, BigInteger, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class Commit(Base):
    """A commit in a tracked repository."""

    __tablename__ = "commits"

    sha: Mapped[str] = mapped_column(CHAR(40), primary_key=True)
    repository_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    author_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    author_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    committer_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    committer_email: Mapped[str | None] = mapped_column(Text, nullable=True)
    commit_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    message: Mapped[str | None] = mapped_column(Text, nullable=True)
