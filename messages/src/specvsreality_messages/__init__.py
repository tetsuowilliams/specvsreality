"""Inbound queue message schemas (one module per message type)."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, TypeAdapter
from pydantic_core import ValidationError

from specvsreality_messages.hello_world import (
    HELLO_WORLD_MESSAGE_TYPE,
    HelloWorldMessage,
)
from specvsreality_messages.init_repo import INIT_REPO_MESSAGE_TYPE, InitRepoMessage
from specvsreality_messages.wind_to_head import WIND_TO_HEAD_MESSAGE_TYPE, WindToHeadMessage

# Union of all concrete messages; extend when adding new types.
WorkerMessage = Annotated[
    HelloWorldMessage | InitRepoMessage | WindToHeadMessage,
    Field(discriminator="message_type"),
]

_worker_message_adapter: TypeAdapter[WorkerMessage] = TypeAdapter(WorkerMessage)

# Keep in sync when adding union members (bootstrap checks handlers cover these).
KNOWN_MESSAGE_TYPES: frozenset[str] = frozenset(
    {
        HELLO_WORLD_MESSAGE_TYPE,
        INIT_REPO_MESSAGE_TYPE,
        WIND_TO_HEAD_MESSAGE_TYPE,
    }
)


def parse_worker_message(raw: str | bytes) -> WorkerMessage:
    """Parse and validate a JSON body into a concrete `WorkerMessage` variant."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return _worker_message_adapter.validate_json(raw)


__all__ = [
    "HELLO_WORLD_MESSAGE_TYPE",
    "HelloWorldMessage",
    "INIT_REPO_MESSAGE_TYPE",
    "InitRepoMessage",
    "WIND_TO_HEAD_MESSAGE_TYPE",
    "WindToHeadMessage",
    "KNOWN_MESSAGE_TYPES",
    "WorkerMessage",
    "parse_worker_message",
    "ValidationError",
]
