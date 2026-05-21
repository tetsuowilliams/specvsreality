"""Unit tests for implements agent wall-clock timeout."""

from __future__ import annotations

import time
from unittest.mock import MagicMock, patch

import pytest

from specvsreality_worker.agents.implements_agent.agent import ImplementsEvaluationAgent
from specvsreality_worker.agents.implements_agent.models import RequirementJustification


def test_evaluate_raises_timeout_when_run_exceeds_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENTS_AGENT_TIMEOUT_SECONDS", "0.05")

    mock_agent = MagicMock()

    def slow_run_sync(*_args, **_kwargs):
        time.sleep(0.2)
        return MagicMock(
            output=RequirementJustification(
                requirement="x",
                implemented=False,
                confidence="low",
                summary="",
            ),
        )

    mock_agent.run_sync = slow_run_sync
    with patch(
        "specvsreality_worker.agents.implements_agent.agent.build_implements_agent",
        return_value=mock_agent,
    ):
        agent = ImplementsEvaluationAgent("test")

        with pytest.raises(TimeoutError, match="timed out"):
            agent.evaluate(
                git_adapter=MagicMock(),
                commit_sha="a" * 40,
                spec_md="# Spec",
                tasks_md=None,
                plan_md=None,
                requirement_id="FR-1",
                requirement_text="Do something",
            )


def test_evaluate_returns_when_run_finishes_in_time(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPLEMENTS_AGENT_TIMEOUT_SECONDS", "5")

    justification = RequirementJustification(
        requirement="Do something",
        implemented=True,
        confidence="high",
        summary="ok",
    )
    mock_agent = MagicMock()
    mock_agent.run_sync.return_value = MagicMock(output=justification)
    with patch(
        "specvsreality_worker.agents.implements_agent.agent.build_implements_agent",
        return_value=mock_agent,
    ):
        agent = ImplementsEvaluationAgent("test")
        result = agent.evaluate(
            git_adapter=MagicMock(),
            commit_sha="a" * 40,
            spec_md="# Spec",
            tasks_md=None,
            plan_md=None,
            requirement_id="FR-1",
            requirement_text="Do something",
        )

    assert result.implemented is True
