"""Unit tests for implements agent limit configuration."""

from __future__ import annotations

import pytest

from specvsreality_worker.agents.implements_agent.settings import (
    implements_agent_timeout_seconds,
    implements_agent_usage_limits,
)


def test_default_timeout_and_usage_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "IMPLEMENTS_AGENT_TIMEOUT_SECONDS",
        "IMPLEMENTS_AGENT_REQUEST_LIMIT",
        "IMPLEMENTS_AGENT_TOOL_CALLS_LIMIT",
    ):
        monkeypatch.delenv(name, raising=False)

    assert implements_agent_timeout_seconds() == 600.0
    limits = implements_agent_usage_limits()
    assert limits.request_limit == 30
    assert limits.tool_calls_limit == 40


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPLEMENTS_AGENT_TIMEOUT_SECONDS", "120")
    monkeypatch.setenv("IMPLEMENTS_AGENT_REQUEST_LIMIT", "10")
    monkeypatch.setenv("IMPLEMENTS_AGENT_TOOL_CALLS_LIMIT", "5")

    assert implements_agent_timeout_seconds() == 120.0
    limits = implements_agent_usage_limits()
    assert limits.request_limit == 10
    assert limits.tool_calls_limit == 5
