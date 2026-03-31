"""Handler contract: one implementation per message type."""

from typing import Any, ClassVar, Protocol, runtime_checkable

from pydantic import BaseModel


@runtime_checkable
class MessageHandler(Protocol):
    """Processes a single `message_type`; `handle` receives the concrete Pydantic model."""

    message_type: ClassVar[str]

    def handle(self, message: BaseModel) -> Any:
        """Run business logic for this message. Exceptions propagate to the processor."""
        ...
