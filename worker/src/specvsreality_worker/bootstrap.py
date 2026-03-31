"""Composition root: factories that wire settings, registry, processor, and consumer."""

from __future__ import annotations

from collections.abc import Iterable

from specvsreality_messages import KNOWN_MESSAGE_TYPES
from specvsreality_worker.config import WorkerSettings, load_settings
from specvsreality_worker.handlers import HelloWorldHandler, MessageHandler
from specvsreality_worker.messaging.consumer import ConnectionFactory, QueueConsumer
from specvsreality_worker.messaging.handler_registry import HandlerRegistry
from specvsreality_worker.messaging.processor import InboundMessageProcessor


def ensure_handlers_cover_messages(registry: HandlerRegistry) -> None:
    """Fail fast if a union member has no handler (drift between messages and bootstrap)."""
    missing = KNOWN_MESSAGE_TYPES - registry.registered_message_types
    if missing:
        types = ", ".join(sorted(missing))
        msg = (
            f"handlers missing for message types: {types}. "
            "Register a handler for each member of WorkerMessage."
        )
        raise RuntimeError(msg)


def default_handlers() -> tuple[MessageHandler, ...]:
    """Default handler set for a standalone worker process."""
    return (HelloWorldHandler(),)


def build_handler_registry(handlers: Iterable[MessageHandler] | None = None) -> HandlerRegistry:
    resolved = tuple(handlers) if handlers is not None else default_handlers()
    registry = HandlerRegistry(resolved)
    ensure_handlers_cover_messages(registry)
    return registry


def build_processor(registry: HandlerRegistry) -> InboundMessageProcessor:
    return InboundMessageProcessor(registry)


def build_consumer(
    settings: WorkerSettings,
    processor: InboundMessageProcessor,
    *,
    connection_factory: ConnectionFactory | None = None,
) -> QueueConsumer:
    return QueueConsumer(settings, processor, connection_factory=connection_factory)


def create_queue_consumer(
    *,
    settings: WorkerSettings | None = None,
    handlers: Iterable[MessageHandler] | None = None,
    connection_factory: ConnectionFactory | None = None,
) -> QueueConsumer:
    """Fully wired `QueueConsumer` (settings → registry → processor → AMQP)."""
    resolved_settings = settings if settings is not None else load_settings()
    registry = build_handler_registry(handlers)
    processor = build_processor(registry)
    return build_consumer(resolved_settings, processor, connection_factory=connection_factory)
