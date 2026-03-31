"""Settings: packaged YAML plus env overrides."""

from __future__ import annotations

import os

import pytest

from specvsreality_worker.config import load_settings


def test_load_settings_reads_packaged_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in list(os.environ):
        if key.startswith("RABBITMQ_"):
            monkeypatch.delenv(key, raising=False)
    s = load_settings()
    assert s.host == "localhost"
    assert s.port == 5672
    assert s.queue_name == "messages"
    assert s.prefetch_count == 1


def test_env_overrides_yaml(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RABBITMQ_HOST", "broker.example")
    monkeypatch.setenv("RABBITMQ_QUEUE_NAME", "custom.queue")
    s = load_settings()
    assert s.host == "broker.example"
    assert s.queue_name == "custom.queue"
