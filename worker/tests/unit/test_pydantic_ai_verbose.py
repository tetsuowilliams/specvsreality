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


@pytest.fixture(autouse=True)
def _clear_verbose_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PYDANTIC_AI_VERBOSE", raising=False)
    monkeypatch.delenv("LOGFIRE_CONSOLE_VERBOSE", raising=False)


def test_verbose_disabled_by_default() -> None:
    assert is_pydantic_ai_verbose() is False
    assert build_event_stream_handler() is None
    assert logfire_console_options() is False


def test_verbose_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYDANTIC_AI_VERBOSE", "1")
    assert is_pydantic_ai_verbose() is True
    assert build_event_stream_handler() is not None
    console = logfire_console_options()
    assert console is not False
    assert getattr(console, "verbose", False) is True


def test_configure_verbose_loggers_sets_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYDANTIC_AI_VERBOSE", "true")
    configure_verbose_loggers()
    assert logging.getLogger("pydantic_ai").level == logging.DEBUG
