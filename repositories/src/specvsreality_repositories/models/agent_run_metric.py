"""Per-run LLM usage metrics for agent invocations."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from specvsreality_repositories.models.base import Base


class AgentRunMetric(Base):
    """Token usage and cost for a single Pydantic AI agent run."""

    __tablename__ = "agent_run_metric"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repo_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("git_repo.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    commit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("commit.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    agent: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(String(255), nullable=False)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6), nullable=False)
    ran_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
