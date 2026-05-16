"""Git repository row: clone location and current commit."""

from __future__ import annotations

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class GitRepo(Base):
    """A tracked git clone on disk."""

    __tablename__ = "git_repo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    cursor_position: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        doc="Git commit SHA (or ref) the clone is pinned to.",
    )
    location: Mapped[str] = mapped_column(
        String(4096),
        nullable=False,
        doc="Absolute path to the clone on the mounted volume.",
    )
