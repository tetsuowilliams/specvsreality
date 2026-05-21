"""RabbitMQ consumer: acknowledgements only; business logic lives in `InboundMessageProcessor`."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pika
from pika.adapters.blocking_connection import BlockingChannel, BlockingConnection

from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.messaging.processor import InboundMessageProcessor, ProcessResult

if TYPE_CHECKING:
    from pika.spec import Basic


ConnectionFactory = Callable[[], BlockingConnection]

_DELIVERY_ERRORS = (
    pika.exceptions.AMQPConnectionError,
    pika.exceptions.ChannelWrongStateError,
    pika.exceptions.ConnectionClosedByBroker,
    pika.exceptions.StreamLostError,
)

_CONNECTION_ERRORS = (
    pika.exceptions.AMQPConnectionError,
    pika.exceptions.StreamLostError,
)


class QueueConsumer:
    """Subscribes to one queue, runs `InboundMessageProcessor` per delivery, then ack/nack."""

    def __init__(
        self,
        settings: WorkerSettings,
        processor: InboundMessageProcessor,
        *,
        connection_factory: ConnectionFactory | None = None,
        log: logging.Logger | None = None,
    ) -> None:
        self._settings = settings
        self._processor = processor
        self._connection_factory: ConnectionFactory = (
            connection_factory if connection_factory is not None else self._open_connection
        )
        self._log = log or logging.getLogger(__name__)
        self._connection: BlockingConnection | None = None
        self._channel: BlockingChannel | None = None
        self._should_stop = False

    def _connection_parameters(self) -> pika.ConnectionParameters:
        credentials = pika.PlainCredentials(self._settings.username, self._settings.password)
        return pika.ConnectionParameters(
            host=self._settings.host,
            port=self._settings.port,
            virtual_host=self._settings.virtual_host,
            credentials=credentials,
            heartbeat=self._settings.heartbeat,
            blocked_connection_timeout=self._settings.blocked_connection_timeout,
        )

    def _open_connection(self) -> BlockingConnection:
        return pika.BlockingConnection(self._connection_parameters())

    def run(self) -> None:
        """Declare the queue and consume until `stop()` or unrecoverable connection loss."""
        self._should_stop = False
        while not self._should_stop:
            try:
                self._consume_once()
            except KeyboardInterrupt:
                raise
            except _CONNECTION_ERRORS as exc:
                self._close_connection()
                if self._should_stop:
                    return
                self._log.warning(
                    "AMQP connection lost (%s); reconnecting in %.1fs",
                    exc,
                    self._settings.reconnect_delay_seconds,
                )
                time.sleep(self._settings.reconnect_delay_seconds)
            else:
                return

    def _consume_once(self) -> None:
        self._connection = self._connection_factory()
        self._channel = self._connection.channel()
        self._channel.basic_qos(prefetch_count=self._settings.prefetch_count)
        self._channel.queue_declare(queue=self._settings.queue_name, durable=True)
        self._channel.basic_consume(
            queue=self._settings.queue_name,
            on_message_callback=self._on_message,
            auto_ack=False,
        )
        self._log.info(
            "consuming queue=%s heartbeat=%ss",
            self._settings.queue_name,
            self._settings.heartbeat,
        )
        assert self._channel is not None
        self._channel.start_consuming()

    def stop(self) -> None:
        """Stop the consumer and close the connection (idempotent)."""
        self._should_stop = True
        if self._channel is not None and self._channel.is_open:
            self._channel.stop_consuming()
        self._close_connection()

    def _close_connection(self) -> None:
        if self._connection is not None and self._connection.is_open:
            self._connection.close()
        self._channel = None
        self._connection = None

    def _on_message(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        _properties: Any,
        body: bytes,
    ) -> None:
        payload = body if isinstance(body, (bytes, bytearray)) else bytes(body)
        result = self._processor.process(payload)
        self._finalize_delivery(channel, method, result)

    def _finalize_delivery(
        self,
        channel: BlockingChannel,
        method: Basic.Deliver,
        result: ProcessResult,
    ) -> None:
        try:
            if result.ok:
                channel.basic_ack(delivery_tag=method.delivery_tag)
                return
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=result.requeue)
        except _DELIVERY_ERRORS as exc:
            self._log.warning(
                "could not finalize delivery_tag=%s ok=%s: %s; "
                "unacked messages are redelivered after reconnect",
                method.delivery_tag,
                result.ok,
                exc,
            )
