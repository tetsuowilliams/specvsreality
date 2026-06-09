"""Publish worker messages to the durable queue (AMQP)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pika
from pydantic import BaseModel

from specvsreality_worker.config import WorkerSettings


def _blocking_publish(body: bytes, settings: WorkerSettings) -> None:
    credentials = pika.PlainCredentials(settings.username, settings.password)
    parameters = pika.ConnectionParameters(
        host=settings.host,
        port=settings.port,
        virtual_host=settings.virtual_host,
        credentials=credentials,
    )
    connection = pika.BlockingConnection(parameters)
    try:
        channel = connection.channel()
        channel.queue_declare(queue=settings.queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=settings.queue_name,
            body=body,
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
    finally:
        if connection.is_open:
            connection.close()


@runtime_checkable
class MessagePublisher(Protocol):
    def publish(self, message: BaseModel, settings: WorkerSettings) -> None:
        """Send a validated message to the configured queue."""
        ...


class PikaMessagePublisher:
    """Blocking Pika client for handler-side enqueue."""

    def publish(self, message: BaseModel, settings: WorkerSettings) -> None:
        body = message.model_dump_json().encode("utf-8")
        _blocking_publish(body, settings)
