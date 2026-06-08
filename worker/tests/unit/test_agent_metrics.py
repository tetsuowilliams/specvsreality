"""Tests for agent metrics recorder."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock

from pydantic_ai.usage import RunUsage

from specvsreality_repositories.models.enums import AgentName
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder
from specvsreality_worker.model_token_cost import ModelTokenCost


def test_recorder_persists_usage_with_computed_cost() -> None:
    repo = MagicMock()
    settings = WorkerSettings(
        model_token_costs={
            "openai:gpt-4o-mini": ModelTokenCost(
                input_per_million=0.15,
                output_per_million=0.60,
            ),
        },
    )
    recorder = AgentMetricsRecorder(
        repo=repo,
        settings=settings,
        repo_id=1,
        commit_id=2,
    )
    ran_at = datetime(2026, 6, 8, tzinfo=UTC)
    usage = RunUsage(input_tokens=1000, output_tokens=500)

    recorder.record(
        agent=AgentName.SPEC_EXTRACTION,
        model="openai:gpt-4o-mini",
        usage=usage,
        ran_at=ran_at,
    )

    repo.record.assert_called_once_with(
        repo_id=1,
        commit_id=2,
        agent=AgentName.SPEC_EXTRACTION,
        model="openai:gpt-4o-mini",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=Decimal("0.000450"),
        ran_at=ran_at,
    )
