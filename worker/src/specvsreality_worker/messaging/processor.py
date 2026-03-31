"""Parse JSON bodies and dispatch to handlers (no AMQP)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from pydantic import ValidationError

from specvsreality_messages import WorkerMessage, parse_worker_message
from specvsreality_worker.messaging.handler_registry import HandlerRegistry

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Outcome of handling a single delivery (drives ack/nack)."""

    ok: bool
    requeue: bool = False


class InboundMessageProcessor:
    """Decode bytes to `WorkerMessage`, dispatch via `HandlerRegistry`, return `ProcessResult`."""

    def __init__(self, registry: HandlerRegistry, *, log: logging.Logger | None = None) -> None:
        self._registry = registry
        self._log = log or logger

    def process(self, body: bytes) -> ProcessResult:
        try:
            text = body.decode("utf-8")
        except UnicodeDecodeError:
            self._log.exception("message body is not valid UTF-8")
            return ProcessResult(ok=False, requeue=False)

        try:
            message = parse_worker_message(text)
        except ValidationError:
            self._log.exception("message failed JSON or schema validation")
            return ProcessResult(ok=False, requeue=False)

        return self._dispatch(message)

    def _dispatch(self, message: WorkerMessage) -> ProcessResult:
        try:
            handler = self._registry.require(message.message_type)
        except KeyError:
            self._log.error("no handler for message_type=%r", message.message_type)
            return ProcessResult(ok=False, requeue=False)

        try:
            handler.handle(message)
        except Exception:
            self._log.exception("handler crashed for message_type=%r", message.message_type)
            return ProcessResult(ok=False, requeue=False)
        return ProcessResult(ok=True)
