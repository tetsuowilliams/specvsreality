"""Versioned requirement content extracted from a spec version."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CHAR,
    JSON,
    BigInteger,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models._types import BigIntPk
from specvsreality_repositories.models.base import Base


class RequirementVersion(Base):
    """One LLM-extracted version of a requirement, tied to a spec version."""

    __tablename__ = "requirement_versions"
    __table_args__ = (
        UniqueConstraint(
            "requirement_id",
            "spec_version_id",
            name="uq_requirement_versions_req_specver",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    requirement_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("requirements.id", ondelete="CASCADE"),
        nullable=False,
    )
    spec_version_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("spec_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(CHAR(40), nullable=False)
    extraction_model: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # LLM-extracted glob hints used by ``CandidateFilter`` to short-circuit
    # blob/requirement pairings that are clearly out of scope. Persisted as a
    # JSON array of strings; an empty list means "no constraint".
    path_globs: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list
    )
    extracted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
