"""Unit tests for implements agent limit configuration."""

from __future__ import annotations

import pytest

from specvsreality_worker.config import WorkerSettings


def test_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "IMPLEMENTS_AGENT_TIMEOUT_SECONDS",
        "IMPLEMENTS_AGENT_REQUEST_LIMIT",
        "IMPLEMENTS_AGENT_BATCH_SIZE",
        "IMPLEMENTS_AGENT_CONCURRENT_BATCHES",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = WorkerSettings(_env_file=None)
    assert settings.implements_agent_timeout_seconds == 600.0
    assert settings.implements_agent_batch_size == 10
    assert settings.implements_agent_concurrent_batches == 10
    assert settings.implements_usage_limits().request_limit == 10


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("IMPLEMENTS_AGENT_TIMEOUT_SECONDS", "120")
    monkeypatch.setenv("IMPLEMENTS_AGENT_REQUEST_LIMIT", "3")
    monkeypatch.setenv("IMPLEMENTS_AGENT_BATCH_SIZE", "8")

    settings = WorkerSettings(_env_file=None)
    assert settings.implements_agent_timeout_seconds == 120.0
    assert settings.implements_agent_batch_size == 8
    assert settings.implements_usage_limits().request_limit == 3


def test_batch_size_floor() -> None:
    settings = WorkerSettings(_env_file=None, implements_agent_batch_size=0)
    assert settings.implements_agent_batch_size == 1


def test_concurrent_batches_floor() -> None:
    settings = WorkerSettings(_env_file=None, implements_agent_concurrent_batches=0)
    assert settings.implements_agent_concurrent_batches == 1
