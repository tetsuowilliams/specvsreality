"""Logfire + Opik wiring for Pydantic AI agents."""

from __future__ import annotations

import logging
import os

from specvsreality_worker.agents.pydantic_ai_verbose import (
    is_pydantic_ai_verbose,
    logfire_console_options,
)

logger = logging.getLogger(__name__)

_DEFAULT_SERVICE_NAME = "specvsreality-worker"

_initialized = False
# True after Logfire/OTLP export and pydantic-ai instrumentation are configured.
logfire_configured: bool = False
# Back-compat alias used by older code paths.
pydantic_ai_otlp_enabled: bool = False


def _set_configured(value: bool) -> None:
    global logfire_configured, pydantic_ai_otlp_enabled
    logfire_configured = value
    pydantic_ai_otlp_enabled = value


def is_logfire_configured() -> bool:
    return logfire_configured


def _logfire_service_name() -> str:
    return os.environ.get("LOGFIRE_SERVICE_NAME", "").strip() or _DEFAULT_SERVICE_NAME


def _logfire_environment() -> str | None:
    value = os.environ.get("LOGFIRE_ENVIRONMENT", "").strip()
    return value or None


def _parse_otlp_headers(raw: str) -> dict[str, str]:
    from opentelemetry.util.re import parse_env_headers

    return parse_env_headers(raw, liberal=True)


def _logfire_configure_kwargs() -> dict[str, object]:
    kwargs: dict[str, object] = {"service_name": _logfire_service_name()}
    environment = _logfire_environment()
    if environment is not None:
        kwargs["environment"] = environment
    return kwargs


def _instrument_pydantic_ai_stack() -> None:
    import logfire

    logfire.instrument_pydantic_ai()
    # OpenAI models use httpx; capture LLM HTTP alongside agent spans.
    logfire.instrument_httpx()


def init_worker_observability() -> None:
    """Configure tracing for Pydantic AI agents.

    Uses Logfire cloud when ``LOGFIRE_TOKEN`` is set (typical for deployed environments).
    Otherwise exports OTLP to Opik when ``OPIK_URL_OVERRIDE`` is set (local/self-hosted).
    If neither is set, Logfire is not configured and the worker runs without tracing export.

    Idempotent; call from the worker process entrypoint after loading ``.env``.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    logfire_token = os.environ.get("LOGFIRE_TOKEN", "").strip()
    if logfire_token:
        try:
            import logfire
        except ImportError:
            logger.exception("logfire missing; install worker deps including logfire")
            return

        logfire.configure(
            token=logfire_token,
            send_to_logfire=True,
            console=logfire_console_options(),
            **_logfire_configure_kwargs(),
        )
        _instrument_pydantic_ai_stack()
        _set_configured(True)
        logger.info(
            "Logfire exporting Pydantic AI traces (service_name=%s, environment=%s%s)",
            _logfire_service_name(),
            _logfire_environment() or "unset",
            ", console_verbose" if is_pydantic_ai_verbose() else "",
        )
        return

    base = os.environ.get("OPIK_URL_OVERRIDE", "").strip().rstrip("/")
    if not base:
        logger.warning(
            "LOGFIRE_TOKEN and OPIK_URL_OVERRIDE unset; Pydantic AI tracing disabled",
        )
        return

    try:
        import logfire
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.exception("logfire or OTLP exporter missing; install worker deps including logfire")
        return

    # Opik ingests at POST {OPIK_URL_OVERRIDE}/v1/private/otel/v1/traces (see opik REST client).
    otlp_endpoint = f"{base}/v1/private/otel/v1/traces"
    headers = os.environ.get("OTEL_EXPORTER_OTLP_HEADERS", "").strip() or None
    exporter = OTLPSpanExporter(
        endpoint=otlp_endpoint,
        headers=_parse_otlp_headers(headers) if headers else None,
    )
    processor = BatchSpanProcessor(exporter)
    logfire.configure(
        send_to_logfire=False,
        console=logfire_console_options(),
        additional_span_processors=[processor],
        metrics=False,
        **_logfire_configure_kwargs(),
    )
    _instrument_pydantic_ai_stack()
    _set_configured(True)
    logger.info(
        "Pydantic AI spans exported via OTLP to %s%s",
        otlp_endpoint,
        " (console verbose)" if is_pydantic_ai_verbose() else "",
    )


def shutdown_worker_observability() -> None:
    """Flush pending spans before process exit."""
    if not logfire_configured:
        return
    try:
        import logfire

        logfire.force_flush()
    except Exception:
        logger.debug("logfire flush on shutdown failed", exc_info=True)
