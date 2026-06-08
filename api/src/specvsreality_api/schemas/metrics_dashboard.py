"""Schemas for the global LLM metrics dashboard."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class MetricsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_cost_usd: Decimal
    total_tokens: int
    total_runs: int
    repo_count: int


class RepoMetricsRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repo_id: int
    repo_name: str
    total_cost_usd: Decimal
    total_tokens: int
    run_count: int


class AgentMetricsRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent: str
    total_cost_usd: Decimal
    total_tokens: int
    run_count: int


class AgentRunRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: int
    repo_id: int
    repo_name: str
    commit_sha: str
    agent: str
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: Decimal
    ran_at: datetime


class MetricsDashboardResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: MetricsSummary
    by_repo: list[RepoMetricsRow]
    by_agent: list[AgentMetricsRow]
    recent_runs: list[AgentRunRow] = Field(default_factory=list)
