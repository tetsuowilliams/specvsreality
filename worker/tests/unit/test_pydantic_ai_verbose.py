"""Unit tests for Pydantic AI verbose mode helpers."""

from __future__ import annotations

import logging

import pytest

from specvsreality_worker.agents.pydantic_ai_verbose import (
    build_event_stream_handler,
    configure_verbose_loggers,
    is_pydantic_ai_verbose,
    logfire_console_options,
)
from specvsreality_worker.config import WorkerSettings


def test_verbose_disabled_by_default() -> None:
    settings = WorkerSettings()
    assert is_pydantic_ai_verbose(settings) is False
    assert build_event_stream_handler(settings) is None
    assert logfire_console_options(settings) is False


def test_verbose_enabled() -> None:
    settings = WorkerSettings(pydantic_ai_verbose=True)
    assert is_pydantic_ai_verbose(settings) is True
    assert build_event_stream_handler(settings) is not None
    console = logfire_console_options(settings)
    assert console is not False
    assert getattr(console, "verbose", False) is True


def test_configure_verbose_loggers_sets_debug() -> None:
    settings = WorkerSettings(pydantic_ai_verbose=True)
    configure_verbose_loggers(settings)
    assert logging.getLogger("pydantic_ai").level == logging.DEBUG


def test_verbose_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYDANTIC_AI_VERBOSE", "1")
    settings = WorkerSettings()
    assert is_pydantic_ai_verbose(settings) is True
