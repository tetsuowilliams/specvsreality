"""Handler for `HelloWorldMessage`."""

from __future__ import annotations

import logging
from typing import ClassVar

from pydantic import BaseModel

from specvsreality_messages.hello_world import HELLO_WORLD_MESSAGE_TYPE, HelloWorldMessage
from specvsreality_worker.handlers.protocol import MessageHandler

logger = logging.getLogger(__name__)


class HelloWorldHandler(MessageHandler):
    """Logs a greeting for each valid `HelloWorldMessage`."""

    message_type: ClassVar[str] = HELLO_WORLD_MESSAGE_TYPE

    def handle(self, message: BaseModel) -> None:
        if not isinstance(message, HelloWorldMessage):
            raise TypeError(f"expected HelloWorldMessage, got {type(message).__name__}")
        logger.info("hello_world name=%s", message.name)
