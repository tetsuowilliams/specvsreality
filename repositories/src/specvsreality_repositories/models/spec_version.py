"""Spec version: the (spec, plan, tasks) blob triplet for a spec."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    CHAR,
    BigInteger,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models._types import BigIntPk
from specvsreality_repositories.models.base import Base


class SpecVersion(Base):
    """An immutable snapshot of a spec defined by its file blobs.

    ``spec_blob_sha`` is required (a spec is identified by the presence of
    ``spec.md``); ``plan_blob_sha`` / ``tasks_blob_sha`` are nullable because
    spec-kit authors often land ``spec.md`` first and add the companions later.
    The unique triplet constraint uses ``NULLS NOT DISTINCT`` so that NULLs
    deduplicate rather than allowing unbounded duplicate rows.
    """

    __tablename__ = "spec_versions"
    __table_args__ = (
        UniqueConstraint(
            "spec_id",
            "spec_blob_sha",
            "plan_blob_sha",
            "tasks_blob_sha",
            name="uq_spec_versions_triplet",
            postgresql_nulls_not_distinct=True,
        ),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    spec_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("specs.id", ondelete="CASCADE"),
        nullable=False,
    )
    spec_blob_sha: Mapped[str] = mapped_column(
        CHAR(40),
        ForeignKey("blobs.sha", ondelete="RESTRICT"),
        nullable=False,
    )
    plan_blob_sha: Mapped[str | None] = mapped_column(
        CHAR(40),
        ForeignKey("blobs.sha", ondelete="RESTRICT"),
        nullable=True,
    )
    tasks_blob_sha: Mapped[str | None] = mapped_column(
        CHAR(40),
        ForeignKey("blobs.sha", ondelete="RESTRICT"),
        nullable=True,
    )
    first_seen_commit: Mapped[str] = mapped_column(
        CHAR(40),
        ForeignKey("commits.sha", ondelete="RESTRICT"),
        nullable=False,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
