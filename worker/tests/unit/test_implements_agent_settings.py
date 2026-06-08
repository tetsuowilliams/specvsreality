"""Unit tests for implements agent limit configuration."""

from __future__ import annotations

import pytest

from specvsreality_worker.config import WorkerSettings


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "IMPLEMENTS_AGENT_TIMEOUT_SECONDS",
        "IMPLEMENTS_AGENT_REQUEST_LIMIT",
        "IMPLEMENTS_AGENT_BATCH_SIZE",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = WorkerSettings()
    assert settings.implements_agent_timeout_seconds == 600.0
    assert settings.implements_agent_batch_size == 5
    assert settings.implements_usage_limits().request_limit == 10


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPLEMENTS_AGENT_TIMEOUT_SECONDS", "120")
    monkeypatch.setenv("IMPLEMENTS_AGENT_REQUEST_LIMIT", "3")
    monkeypatch.setenv("IMPLEMENTS_AGENT_BATCH_SIZE", "8")

    settings = WorkerSettings()
    assert settings.implements_agent_timeout_seconds == 120.0
    assert settings.implements_agent_batch_size == 8
    assert settings.implements_usage_limits().request_limit == 3


def test_batch_size_floor() -> None:
    settings = WorkerSettings(implements_agent_batch_size=0)
    assert settings.implements_agent_batch_size == 1
