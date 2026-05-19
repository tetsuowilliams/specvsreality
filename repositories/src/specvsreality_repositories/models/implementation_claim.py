"""Append-only LLM verdict that a blob implements a requirement version."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    DateTime,
    Float,
    ForeignKey,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models._types import BigIntPk
from specvsreality_repositories.models.base import Base


class ImplementationClaim(Base):
    """A judgment row: never updated, never deleted."""

    __tablename__ = "implementation_claims"

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    requirement_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("requirement_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    blob_sha: Mapped[str] = mapped_column(
        CHAR(40),
        ForeignKey("blobs.sha", ondelete="RESTRICT"),
        nullable=False,
    )
    verdict: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    model_version: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
