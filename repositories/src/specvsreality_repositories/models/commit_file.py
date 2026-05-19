"""Path -> blob mapping at a commit."""

from __future__ import annotations

from sqlalchemy import CHAR, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class CommitFile(Base):
    """One file (path, blob, mode) present at a commit's tree."""

    __tablename__ = "commit_files"

    commit_sha: Mapped[str] = mapped_column(
        CHAR(40),
        ForeignKey("commits.sha", ondelete="CASCADE"),
        primary_key=True,
    )
    path: Mapped[str] = mapped_column(Text, primary_key=True)
    blob_sha: Mapped[str] = mapped_column(
        CHAR(40),
        ForeignKey("blobs.sha", ondelete="RESTRICT"),
        nullable=False,
    )
    mode: Mapped[str | None] = mapped_column(Text, nullable=True)
