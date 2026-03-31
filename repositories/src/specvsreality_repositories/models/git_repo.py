"""Git repository row: clone location and current commit."""

from __future__ import annotations

import uuid

from sqlalchemy import String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class GitRepo(Base):
    """A tracked git clone on disk."""

    __tablename__ = "git_repo"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
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
