"""Assemble global LLM metrics dashboard response."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_api.schemas.metrics_dashboard import (
    AgentMetricsRow,
    AgentRunRow,
    MetricsDashboardResponse,
    MetricsSummary,
    RepoMetricsRow,
)
from specvsreality_repositories.repos import create_agent_run_metric_repo


class MetricsDashboardFacade:
    def __init__(self, session: Session) -> None:
        self._repo = create_agent_run_metric_repo(session)

    def get_dashboard(
        self,
        *,
        repo_id: int | None = None,
        recent_limit: int = 50,
    ) -> MetricsDashboardResponse:
        totals = self._repo.global_totals()
        summary = MetricsSummary(
            total_cost_usd=totals.total_cost_usd,
            total_tokens=totals.total_tokens,
            total_runs=totals.total_runs,
            repo_count=totals.repo_count,
        )
        by_repo = [
            RepoMetricsRow(
                repo_id=row.repo_id,
                repo_name=row.repo_name,
                total_cost_usd=row.total_cost_usd,
                total_tokens=row.total_tokens,
                run_count=row.run_count,
            )
            for row in self._repo.aggregate_by_repo()
        ]
        by_agent = [
            AgentMetricsRow(
                agent=row.agent,
                total_cost_usd=row.total_cost_usd,
                total_tokens=row.total_tokens,
                run_count=row.run_count,
            )
            for row in self._repo.aggregate_by_agent()
        ]
        recent_runs = [
            AgentRunRow(
                id=row.id,
                repo_id=row.repo_id,
                repo_name=row.repo_name,
                commit_sha=row.commit_sha,
                agent=row.agent,
                model=row.model,
                input_tokens=row.input_tokens,
                output_tokens=row.output_tokens,
                total_tokens=row.total_tokens,
                cost_usd=row.cost_usd,
                ran_at=row.ran_at,
            )
            for row in self._repo.list_recent_runs(limit=recent_limit, repo_id=repo_id)
        ]
        return MetricsDashboardResponse(
            summary=summary,
            by_repo=by_repo,
            by_agent=by_agent,
            recent_runs=recent_runs,
        )
