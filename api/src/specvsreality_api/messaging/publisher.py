"""Publish raw bytes to the durable `messages` queue (AMQP)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pika
from fastapi.concurrency import run_in_threadpool

from specvsreality_api.config import Settings


def _blocking_publish(body: bytes, settings: Settings) -> None:
    credentials = pika.PlainCredentials(settings.rabbitmq_username, settings.rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        virtual_host=settings.rabbitmq_virtual_host,
        credentials=credentials,
    )
    connection = pika.BlockingConnection(parameters)
    try:
        channel = connection.channel()
        channel.queue_declare(queue=settings.rabbitmq_queue_name, durable=True)
        channel.basic_publish(
            exchange="",
            routing_key=settings.rabbitmq_queue_name,
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
    async def publish(self, body: bytes, settings: Settings) -> None:
        """Send payload to the configured queue."""
        ...


class PikaMessagePublisher:
    """Blocking Pika client wrapped for FastAPI async routes."""

    async def publish(self, body: bytes, settings: Settings) -> None:
        await run_in_threadpool(_blocking_publish, body, settings)
