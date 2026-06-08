"""Structured spec item extracted from a spec version."""

from __future__ import annotations

from sqlalchemy import Enum as SaEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base
from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType


class SpecItem(Base):
    """A single implementation-verifiable obligation within a spec version."""

    __tablename__ = "spec_item"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    spec_version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("spec_version.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    local_key: Mapped[str] = mapped_column(
        String,
        nullable=False,
        comment=(
            "Identifier within this spec version, e.g. FR-003, AC-002, OBL-004. "
            "Used for display and local reference only."
        ),
    )
    item_type: Mapped[SpecItemType] = mapped_column(
        SaEnum(
            SpecItemType,
            name="spec_item_type",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        comment="Type of item, e.g. functional_behavior, acceptance_scenario, context.",
    )
    text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Original or near-original item text extracted from the spec bundle.",
    )
    source_quote: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Short exact quote from the source document supporting this item.",
    )
    importance: Mapped[SpecItemImportance] = mapped_column(
        SaEnum(
            SpecItemImportance,
            name="spec_item_importance",
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
        comment="How strongly the item should be enforced: must, should, optional, context.",
    )
    success_criteria: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        comment="Concrete evidence that would indicate this item is satisfied.",
    )
    failure_criteria: Mapped[list[str]] = mapped_column(
        ARRAY(String),
        nullable=False,
        default=list,
        comment="Concrete evidence that would indicate this item is not satisfied.",
    )
