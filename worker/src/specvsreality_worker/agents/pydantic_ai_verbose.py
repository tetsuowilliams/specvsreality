"""Optional verbose logging for Pydantic AI agent runs."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterable
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from specvsreality_worker.config import WorkerSettings

logger = logging.getLogger(__name__)

_VERBOSE_LOGGERS = (
    "pydantic_ai",
    "openai",
    "httpx",
    "httpcore",
)


def is_pydantic_ai_verbose(settings: WorkerSettings) -> bool:
    """True when verbose console logging is enabled in worker settings."""
    return settings.pydantic_ai_verbose_enabled


def configure_verbose_loggers(settings: WorkerSettings) -> None:
    """Raise log level for Pydantic AI and HTTP client libraries."""
    if not is_pydantic_ai_verbose(settings):
        return
    for name in _VERBOSE_LOGGERS:
        logging.getLogger(name).setLevel(logging.DEBUG)
    logger.info("Pydantic AI verbose logging enabled for %s", ", ".join(_VERBOSE_LOGGERS))


def logfire_console_options(settings: WorkerSettings) -> object | bool:
    """Logfire ``console`` kwarg for ``logfire.configure``."""
    if not is_pydantic_ai_verbose(settings):
        return False
    import logfire

    return logfire.ConsoleOptions(
        verbose=True,
        min_log_level="debug",
        span_style="indented",
    )


def _event_summary(event: object) -> str:
    kind = getattr(event, "event_kind", type(event).__name__)
    tool_name = getattr(event, "tool_name", None)
    if tool_name is not None:
        return f"{kind} tool={tool_name!r}"
    part = getattr(event, "part", None)
    if part is not None:
        part_kind = getattr(part, "part_kind", type(part).__name__)
        return f"{kind} part={part_kind}"
    return str(kind)


def build_event_stream_handler(settings: WorkerSettings) -> Any | None:
    """Return an async handler for ``Agent.run_sync(..., event_stream_handler=...)``."""
    if not is_pydantic_ai_verbose(settings):
        return None

    async def _handler(_ctx: object, stream: AsyncIterable[object]) -> None:
        async for event in stream:
            name = type(event).__name__
            if name == "PartDeltaEvent":
                continue
            logger.info("pydantic_ai %s %s", name, _event_summary(event))

    return _handler
