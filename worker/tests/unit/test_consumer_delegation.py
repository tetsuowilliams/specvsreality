"""Queue consumer delegates to processor and ack/nack."""

from __future__ import annotations

import logging
from unittest.mock import Mock

import pytest

from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.handlers import HelloWorldHandler
from specvsreality_worker.messaging.consumer import QueueConsumer
from specvsreality_worker.messaging.handler_registry import HandlerRegistry
from specvsreality_worker.messaging.processor import InboundMessageProcessor, ProcessResult


def test_finalize_delivery_acks_on_success(worker_settings: WorkerSettings) -> None:
    processor = Mock(spec=InboundMessageProcessor)
    consumer = QueueConsumer(worker_settings, processor)
    channel = Mock()
    method = Mock()
    method.delivery_tag = 99
    consumer._finalize_delivery(channel, method, ProcessResult(ok=True))
    channel.basic_ack.assert_called_once_with(delivery_tag=99)
    channel.basic_nack.assert_not_called()


def test_finalize_delivery_nacks_on_failure(worker_settings: WorkerSettings) -> None:
    processor = Mock(spec=InboundMessageProcessor)
    consumer = QueueConsumer(worker_settings, processor)
    channel = Mock()
    method = Mock(delivery_tag=5)
    consumer._finalize_delivery(channel, method, ProcessResult(ok=False, requeue=False))
    channel.basic_nack.assert_called_once_with(delivery_tag=5, requeue=False)
    channel.basic_ack.assert_not_called()


def test_on_message_runs_processor_and_acks(
    worker_settings: WorkerSettings,
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO)
    registry = HandlerRegistry([HelloWorldHandler()])
    processor = InboundMessageProcessor(registry)
    consumer = QueueConsumer(worker_settings, processor)
    channel = Mock()
    method = Mock(delivery_tag=12)
    body = b'{"message_type":"hello_world","name":"Test"}'
    consumer._on_message(channel, method, None, body)
    assert any("Test" in r.getMessage() for r in caplog.records)
    channel.basic_ack.assert_called_once_with(delivery_tag=12)
