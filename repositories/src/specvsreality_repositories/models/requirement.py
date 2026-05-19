"""Logical requirement under a spec, identified by external_id."""

from __future__ import annotations

from sqlalchemy import BigInteger, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models._types import BigIntPk
from specvsreality_repositories.models.base import Base


class Requirement(Base):
    """A stable requirement identity that may have many versions over time."""

    __tablename__ = "requirements"
    __table_args__ = (
        UniqueConstraint(
            "spec_id", "external_id", name="uq_requirements_spec_external_id"
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    spec_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("specs.id", ondelete="CASCADE"),
        nullable=False,
    )
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
