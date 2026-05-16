"""Inbound queue message schemas (one module per message type)."""

from __future__ import annotations

from typing import Annotated

from pydantic import Field, TypeAdapter
from pydantic_core import ValidationError

from specvsreality_messages.hello_world import (
    HELLO_WORLD_MESSAGE_TYPE,
    HelloWorldMessage,
)
from specvsreality_messages.scan_repo import SCAN_REPO_MESSAGE_TYPE, ScanRepoMessage

# Union of all concrete messages; extend when adding new types.
WorkerMessage = Annotated[
    HelloWorldMessage | ScanRepoMessage,
    Field(discriminator="message_type"),
]

_worker_message_adapter: TypeAdapter[WorkerMessage] = TypeAdapter(WorkerMessage)

# Keep in sync when adding union members (bootstrap checks handlers cover these).
KNOWN_MESSAGE_TYPES: frozenset[str] = frozenset({HELLO_WORLD_MESSAGE_TYPE, SCAN_REPO_MESSAGE_TYPE})


def parse_worker_message(raw: str | bytes) -> WorkerMessage:
    """Parse and validate a JSON body into a concrete `WorkerMessage` variant."""
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8")
    return _worker_message_adapter.validate_json(raw)


__all__ = [
    "HELLO_WORLD_MESSAGE_TYPE",
    "HelloWorldMessage",
    "SCAN_REPO_MESSAGE_TYPE",
    "ScanRepoMessage",
    "KNOWN_MESSAGE_TYPES",
    "WorkerMessage",
    "parse_worker_message",
    "ValidationError",
]
