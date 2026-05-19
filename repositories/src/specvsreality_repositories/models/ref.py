"""Branch / tag pointer."""

from __future__ import annotations

from sqlalchemy import CHAR, BigInteger, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models._types import BigIntPk
from specvsreality_repositories.models.base import Base


class Ref(Base):
    """A git ref (branch or tag) pointing at a commit."""

    __tablename__ = "refs"
    __table_args__ = (
        UniqueConstraint("repository_id", "name", name="uq_refs_repo_name"),
    )

    id: Mapped[int] = mapped_column(BigIntPk, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    ref_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_sha: Mapped[str] = mapped_column(CHAR(40), nullable=False)
