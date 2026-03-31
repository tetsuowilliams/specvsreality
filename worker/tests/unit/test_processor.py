"""Inbound processor: parse and dispatch without AMQP."""

from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from specvsreality_messages.hello_world import HELLO_WORLD_MESSAGE_TYPE, HelloWorldMessage
from specvsreality_worker.handlers.protocol import MessageHandler
from specvsreality_worker.messaging.handler_registry import HandlerRegistry
from specvsreality_worker.messaging.processor import InboundMessageProcessor, ProcessResult


def test_processor_dispatches_valid_message() -> None:
    sink: list[str] = []
    registry = HandlerRegistry([_HelloWorldCapture(sink)])
    processor = InboundMessageProcessor(registry)
    body = b'{"message_type":"hello_world","name":"Grace"}'
    assert processor.process(body) == ProcessResult(ok=True)
    assert sink == ["Grace"]


def test_processor_invalid_body_utf8() -> None:
    registry = HandlerRegistry([_HelloWorldCapture([])])
    processor = InboundMessageProcessor(registry)
    result = processor.process(b"\xff\xfe")
    assert result == ProcessResult(ok=False, requeue=False)


def test_processor_invalid_json() -> None:
    registry = HandlerRegistry([_HelloWorldCapture([])])
    processor = InboundMessageProcessor(registry)
    result = processor.process(b"not-json")
    assert result.ok is False


def test_processor_unknown_discriminator() -> None:
    registry = HandlerRegistry([_HelloWorldCapture([])])
    processor = InboundMessageProcessor(registry)
    body = b'{"message_type":"missing","foo":1}'
    result = processor.process(body)
    assert result.ok is False


def test_processor_missing_handler_returns_failure() -> None:
    """Registry without handler for parsed type (misconfiguration)."""

    class OrphanHandler(MessageHandler):
        message_type: ClassVar[str] = "unused"

        def handle(self, message: BaseModel) -> None:
            raise AssertionError

    registry = HandlerRegistry([OrphanHandler()])
    processor = InboundMessageProcessor(registry)
    body = b'{"message_type":"hello_world","name":"X"}'
    result = processor.process(body)
    assert result.ok is False


def test_processor_handler_exception_returns_failure() -> None:
    class Boom(MessageHandler):
        message_type: ClassVar[str] = HELLO_WORLD_MESSAGE_TYPE

        def handle(self, message: BaseModel) -> None:
            msg = HelloWorldMessage.model_validate(message.model_dump())
            raise RuntimeError(msg.name)

    registry = HandlerRegistry([Boom()])
    processor = InboundMessageProcessor(registry)
    body = b'{"message_type":"hello_world","name":"fail"}'
    result = processor.process(body)
    assert result.ok is False


class _HelloWorldCapture(MessageHandler):
    message_type: ClassVar[str] = HELLO_WORLD_MESSAGE_TYPE

    def __init__(self, sink: list[str]) -> None:
        self._sink = sink

    def handle(self, message: BaseModel) -> None:
        m = HelloWorldMessage.model_validate(message.model_dump())
        self._sink.append(m.name)
