"""Contract tests for queue message parsing."""

from __future__ import annotations

import pytest
from pydantic_core import ValidationError

from specvsreality_messages import (
    HelloWorldMessage,
    parse_worker_message,
)


def test_hello_world_round_trip_json() -> None:
    raw = '{"message_type":"hello_world","name":"Ada"}'
    msg = parse_worker_message(raw)
    assert isinstance(msg, HelloWorldMessage)
    assert msg.name == "Ada"


def test_hello_world_model_dump_json() -> None:
    m = HelloWorldMessage(name="Grace")
    text = m.model_dump_json()
    again = parse_worker_message(text)
    assert again.name == "Grace"


def test_invalid_discriminator() -> None:
    with pytest.raises(ValidationError):
        parse_worker_message('{"message_type":"nope","name":"x"}')
