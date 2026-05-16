"""Opik + Logfire wiring for Pydantic AI agents (OTLP to local or remote Opik)."""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_initialized = False
pydantic_ai_otlp_enabled: bool = False


def init_worker_observability() -> None:
    """Configure Logfire OTLP export to Opik when ``OPIK_URL_OVERRIDE`` is set.

    Uses Opik's OTLP ingest path under the API base URL (self-hosted: ``.../api/v1/private/otel``).
    The value must be the real Opik REST API base; pointing it at a non-Opik server
    (wrong host/port) breaks OTLP export and Opik ``session/redirect`` links.
    Idempotent; safe to call from the worker process entrypoint only.
    """
    global _initialized
    if _initialized:
        return
    _initialized = True

    base = os.environ.get("OPIK_URL_OVERRIDE", "").strip().rstrip("/")
    if not base:
        logger.debug("OPIK_URL_OVERRIDE unset; skipping Logfire/Opik OTLP init for Pydantic AI")
        return

    try:
        import logfire
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except ImportError:
        logger.exception("logfire or OTLP exporter missing; install worker deps including logfire")
        return

    otlp_endpoint = f"{base}/v1/private/otel"
    exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    processor = BatchSpanProcessor(exporter)
    logfire.configure(
        send_to_logfire=False,
        console=False,
        additional_span_processors=[processor],
        metrics=False,
    )
    logfire.instrument_pydantic_ai()
    global pydantic_ai_otlp_enabled
    pydantic_ai_otlp_enabled = True
    logger.info("Pydantic AI spans exported via OTLP to %s", otlp_endpoint)
