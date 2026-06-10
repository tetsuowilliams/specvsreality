"""Tests for agent run metric repository."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import AgentName
from specvsreality_repositories.repos import create_agent_run_metric_repo


@pytest.fixture()
def metric_repo(db_session: Session):
    return create_agent_run_metric_repo(db_session)


def test_record_and_aggregate(
    metric_repo,
    git_repo_id: int,
    commit_id: int,
) -> None:
    ran_at = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    metric_repo.record(
        repo_id=git_repo_id,
        commit_id=commit_id,
        agent=AgentName.SPEC_EXTRACTION,
        model="openai:gpt-4o-mini",
        input_tokens=1000,
        output_tokens=500,
        cost_usd=Decimal("0.000450"),
        ran_at=ran_at,
    )
    metric_repo.record(
        repo_id=git_repo_id,
        commit_id=commit_id,
        agent=AgentName.IMPLEMENTS,
        model="openai:gpt-4o-mini",
        input_tokens=2000,
        output_tokens=1000,
        cost_usd=Decimal("0.000900"),
        ran_at=ran_at,
    )

    totals = metric_repo.global_totals()
    assert totals.total_runs == 2
    assert totals.total_tokens == 4500
    assert totals.total_cost_usd == Decimal("0.001350")
    assert totals.repo_count == 1

    by_repo = metric_repo.aggregate_by_repo()
    assert len(by_repo) == 1
    assert by_repo[0].repo_id == git_repo_id
    assert by_repo[0].run_count == 2
    assert by_repo[0].total_tokens == 4500

    by_agent = metric_repo.aggregate_by_agent()
    assert len(by_agent) == 2
    agents = {row.agent for row in by_agent}
    assert agents == {AgentName.SPEC_EXTRACTION.value, AgentName.IMPLEMENTS.value}

    recent = metric_repo.list_recent_runs(limit=10)
    assert len(recent) == 2
    assert recent[0].commit_sha == "a" * 40
    assert recent[0].repo_name == "repo"

    filtered = metric_repo.list_recent_runs(limit=10, repo_id=git_repo_id)
    assert len(filtered) == 2


def test_aggregates_return_empty_when_no_data(metric_repo) -> None:
    totals = metric_repo.global_totals()
    assert totals.total_runs == 0
    assert totals.total_tokens == 0
    assert totals.repo_count == 0
    assert metric_repo.aggregate_by_repo() == []
    assert metric_repo.aggregate_by_agent() == []
    assert metric_repo.list_recent_runs(limit=10) == []


def test_list_recent_runs_filters_by_repo_id(
    db_session: Session,
    metric_repo,
    git_repo_id: int,
    commit_id: int,
) -> None:
    from datetime import UTC, datetime
    from decimal import Decimal

    from tests.fixtures.graph import add_git_repo

    other_repo_id = add_git_repo(
        db_session,
        name="other",
        url="https://example.test/other.git",
    ).id
    ran_at = datetime(2026, 6, 8, 12, 0, tzinfo=UTC)
    metric_repo.record(
        repo_id=git_repo_id,
        commit_id=commit_id,
        agent=AgentName.SPEC_EXTRACTION,
        model="openai:gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.0001"),
        ran_at=ran_at,
    )

    assert len(metric_repo.list_recent_runs(limit=10, repo_id=other_repo_id)) == 0
