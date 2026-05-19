"""Content-addressed git blob."""

from __future__ import annotations

from sqlalchemy import CHAR, BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class Blob(Base):
    """A git blob keyed by SHA-1 hash."""

    __tablename__ = "blobs"

    sha: Mapped[str] = mapped_column(CHAR(40), primary_key=True)
    size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    storage_url: Mapped[str | None] = mapped_column(Text, nullable=True)
