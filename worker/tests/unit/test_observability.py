"""Observability init must not require local ``logfire auth``."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from specvsreality_worker import observability
from specvsreality_worker.config import WorkerSettings


@pytest.fixture(autouse=True)
def _reset_observability_state() -> None:
    observability._initialized = False
    observability._set_configured(False)
    yield
    observability._initialized = False
    observability._set_configured(False)


def test_init_without_credentials_does_not_raise() -> None:
    settings = WorkerSettings(logfire_token="", opik_url_override="")
    observability.init_worker_observability(settings)
    assert observability.is_logfire_configured() is False


def test_init_with_logfire_token_enables_tracing() -> None:
    settings = WorkerSettings(logfire_token="test-write-token", opik_url_override="")
    observability.init_worker_observability(settings)
    assert observability.is_logfire_configured() is True


def test_logfire_configure_uses_token_and_instruments() -> None:
    settings = WorkerSettings(
        logfire_token="test-write-token",
        logfire_service_name="my-worker",
        logfire_environment="staging",
        opik_url_override="",
    )

    with (
        patch("logfire.configure") as configure,
        patch("logfire.instrument_pydantic_ai") as instrument_pai,
        patch("logfire.instrument_httpx") as instrument_httpx,
    ):
        observability.init_worker_observability(settings)

    configure.assert_called_once()
    assert configure.call_args.kwargs["token"] == "test-write-token"
    assert configure.call_args.kwargs["send_to_logfire"] is True
    assert configure.call_args.kwargs["service_name"] == "my-worker"
    assert configure.call_args.kwargs["environment"] == "staging"
    instrument_pai.assert_called_once()
    instrument_httpx.assert_called_once()


def test_init_with_opik_uses_full_otlp_traces_endpoint() -> None:
    settings = WorkerSettings(
        logfire_token="",
        opik_url_override="http://localhost:5173/api",
    )

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
        observability.init_worker_observability(settings)

    exporter_cls.assert_called_once()
    assert exporter_cls.call_args.kwargs["endpoint"] == (
        "http://localhost:5173/api/v1/private/otel/v1/traces"
    )
    processor_cls.assert_called_once()
    configure.assert_called_once()
    assert configure.call_args.kwargs["send_to_logfire"] is False
