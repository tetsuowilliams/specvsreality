"""Repository access for agent run metrics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.agent_run_metric import AgentRunMetric
from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.enums import AgentName
from specvsreality_repositories.models.git_repo import GitRepo


@dataclass(frozen=True)
class GlobalTotalsRow:
    total_cost_usd: Decimal
    total_tokens: int
    total_runs: int
    repo_count: int


@dataclass(frozen=True)
class RepoAggregateRow:
    repo_id: int
    repo_name: str
    total_cost_usd: Decimal
    total_tokens: int
    run_count: int


@dataclass(frozen=True)
class AgentAggregateRow:
    agent: str
    total_cost_usd: Decimal
    total_tokens: int
    run_count: int


@dataclass(frozen=True)
class RecentRunRow:
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


class AgentRunMetricRepo:
    """Read/write access for ``agent_run_metric`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def record(
        self,
        *,
        repo_id: int,
        commit_id: int,
        agent: AgentName,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: Decimal,
        ran_at: datetime,
    ) -> AgentRunMetric:
        row = AgentRunMetric(
            repo_id=repo_id,
            commit_id=commit_id,
            agent=agent.value,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=cost_usd,
            ran_at=ran_at,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def global_totals(self) -> GlobalTotalsRow:
        stmt = select(
            func.coalesce(func.sum(AgentRunMetric.cost_usd), 0),
            func.coalesce(func.sum(AgentRunMetric.total_tokens), 0),
            func.count(AgentRunMetric.id),
            func.count(func.distinct(AgentRunMetric.repo_id)),
        )
        cost, tokens, runs, repo_count = self._session.execute(stmt).one()
        return GlobalTotalsRow(
            total_cost_usd=Decimal(str(cost)),
            total_tokens=int(tokens),
            total_runs=int(runs),
            repo_count=int(repo_count),
        )

    def aggregate_by_repo(self) -> list[RepoAggregateRow]:
        stmt = (
            select(
                AgentRunMetric.repo_id,
                GitRepo.name,
                func.sum(AgentRunMetric.cost_usd),
                func.sum(AgentRunMetric.total_tokens),
                func.count(AgentRunMetric.id),
            )
            .join(GitRepo, GitRepo.id == AgentRunMetric.repo_id)
            .group_by(AgentRunMetric.repo_id, GitRepo.name)
            .order_by(func.sum(AgentRunMetric.cost_usd).desc())
        )
        rows = self._session.execute(stmt).all()
        return [
            RepoAggregateRow(
                repo_id=repo_id,
                repo_name=repo_name,
                total_cost_usd=Decimal(str(total_cost)),
                total_tokens=int(total_tokens),
                run_count=int(run_count),
            )
            for repo_id, repo_name, total_cost, total_tokens, run_count in rows
        ]

    def aggregate_by_agent(self) -> list[AgentAggregateRow]:
        stmt = (
            select(
                AgentRunMetric.agent,
                func.sum(AgentRunMetric.cost_usd),
                func.sum(AgentRunMetric.total_tokens),
                func.count(AgentRunMetric.id),
            )
            .group_by(AgentRunMetric.agent)
            .order_by(func.sum(AgentRunMetric.cost_usd).desc())
        )
        rows = self._session.execute(stmt).all()
        return [
            AgentAggregateRow(
                agent=agent,
                total_cost_usd=Decimal(str(total_cost)),
                total_tokens=int(total_tokens),
                run_count=int(run_count),
            )
            for agent, total_cost, total_tokens, run_count in rows
        ]

    def list_recent_runs(
        self,
        *,
        limit: int = 50,
        repo_id: int | None = None,
    ) -> list[RecentRunRow]:
        stmt = (
            select(
                AgentRunMetric,
                GitRepo.name,
                Commit.commit_sha,
            )
            .join(GitRepo, GitRepo.id == AgentRunMetric.repo_id)
            .join(Commit, Commit.id == AgentRunMetric.commit_id)
            .order_by(AgentRunMetric.ran_at.desc())
            .limit(limit)
        )
        if repo_id is not None:
            stmt = stmt.where(AgentRunMetric.repo_id == repo_id)

        rows = self._session.execute(stmt).all()
        return [
            RecentRunRow(
                id=metric.id,
                repo_id=metric.repo_id,
                repo_name=repo_name,
                commit_sha=commit_sha,
                agent=metric.agent,
                model=metric.model,
                input_tokens=metric.input_tokens,
                output_tokens=metric.output_tokens,
                total_tokens=metric.total_tokens,
                cost_usd=metric.cost_usd,
                ran_at=metric.ran_at,
            )
            for metric, repo_name, commit_sha in rows
        ]


def create_agent_run_metric_repo(session: Session) -> AgentRunMetricRepo:
    return AgentRunMetricRepo(session)
