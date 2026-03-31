"""Maps `message_type` strings to handlers (built at startup)."""

from __future__ import annotations

from collections.abc import Iterable

from specvsreality_worker.handlers.protocol import MessageHandler


class HandlerRegistry:
    """Registry of `MessageHandler` instances keyed by `message_type`."""

    def __init__(self, handlers: Iterable[MessageHandler]) -> None:
        self._handlers: dict[str, MessageHandler] = {}
        for handler in handlers:
            key = handler.message_type
            if key in self._handlers:
                msg = f"duplicate handler for message_type={key!r}"
                raise ValueError(msg)
            self._handlers[key] = handler

    @property
    def registered_message_types(self) -> frozenset[str]:
        return frozenset(self._handlers.keys())

    def require(self, message_type: str) -> MessageHandler:
        """Return the handler for `message_type` or raise `KeyError`."""
        return self._handlers[message_type]
