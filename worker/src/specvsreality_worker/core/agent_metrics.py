"""Record per-run LLM usage metrics to the database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from pydantic_ai.usage import RunUsage

from specvsreality_repositories.models.enums import AgentName
from specvsreality_repositories.repos import AgentRunMetricRepo
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.model_token_cost import calculate_cost_usd


@dataclass
class AgentMetricsRecorder:
    """Persists token usage for a single commit scan."""

    repo: AgentRunMetricRepo
    settings: WorkerSettings
    repo_id: int
    commit_id: int

    def record(
        self,
        *,
        agent: AgentName,
        model: str,
        usage: RunUsage,
        ran_at: datetime | None = None,
    ) -> None:
        cost_usd = calculate_cost_usd(
            self.settings.model_token_costs,
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
        )
        self.repo.record(
            repo_id=self.repo_id,
            commit_id=self.commit_id,
            agent=agent,
            model=model,
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=cost_usd,
            ran_at=ran_at or datetime.now(UTC),
        )
