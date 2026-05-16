"""Links a requirement version to an artifact version."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class Implements(Base):
    """Many-to-many: which artifact versions implement a requirement version."""

    __tablename__ = "implements"

    requirement_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("requirement_version.id", ondelete="CASCADE"),
        primary_key=True,
    )
    artifact_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("artifact_version.id", ondelete="CASCADE"),
        primary_key=True,
    )
