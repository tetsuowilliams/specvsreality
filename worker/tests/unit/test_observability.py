"""Observability init must not require local ``logfire auth``."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from specvsreality_worker import observability


@pytest.fixture(autouse=True)
def _reset_observability_state() -> None:
    observability._initialized = False
    observability._set_configured(False)
    yield
    observability._initialized = False
    observability._set_configured(False)


def test_init_without_credentials_does_not_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    monkeypatch.delenv("OPIK_URL_OVERRIDE", raising=False)
    observability.init_worker_observability()
    assert observability.is_logfire_configured() is False


def test_init_with_logfire_token_enables_tracing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGFIRE_TOKEN", "test-write-token")
    monkeypatch.delenv("OPIK_URL_OVERRIDE", raising=False)
    observability.init_worker_observability()
    assert observability.is_logfire_configured() is True


def test_logfire_configure_uses_token_and_instruments(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGFIRE_TOKEN", "test-write-token")
    monkeypatch.setenv("LOGFIRE_SERVICE_NAME", "my-worker")
    monkeypatch.setenv("LOGFIRE_ENVIRONMENT", "staging")
    monkeypatch.delenv("OPIK_URL_OVERRIDE", raising=False)

    with (
        patch("logfire.configure") as configure,
        patch("logfire.instrument_pydantic_ai") as instrument_pai,
        patch("logfire.instrument_httpx") as instrument_httpx,
    ):
        observability.init_worker_observability()

    configure.assert_called_once()
    assert configure.call_args.kwargs["token"] == "test-write-token"
    assert configure.call_args.kwargs["send_to_logfire"] is True
    assert configure.call_args.kwargs["service_name"] == "my-worker"
    assert configure.call_args.kwargs["environment"] == "staging"
    instrument_pai.assert_called_once()
    instrument_httpx.assert_called_once()


def test_init_with_opik_uses_full_otlp_traces_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LOGFIRE_TOKEN", raising=False)
    monkeypatch.setenv("OPIK_URL_OVERRIDE", "http://localhost:5173/api")

    with (
        patch("logfire.configure") as configure,
        patch("logfire.instrument_pydantic_ai"),
        patch("logfire.instrument_httpx"),
        patch(
            "opentelemetry.exporter.otlp.proto.http.trace_exporter.OTLPSpanExporter",
        ) as exporter_cls,
        patch(
            "opentelemetry.sdk.trace.export.BatchSpanProcessor",
        ) as processor_cls,
    ):
        observability.init_worker_observability()

    exporter_cls.assert_called_once()
    assert exporter_cls.call_args.kwargs["endpoint"] == (
        "http://localhost:5173/api/v1/private/otel/v1/traces"
    )
    processor_cls.assert_called_once()
    configure.assert_called_once()
    assert configure.call_args.kwargs["send_to_logfire"] is False
