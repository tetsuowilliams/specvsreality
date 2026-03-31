"""Liveness and dependency checks."""

from __future__ import annotations

from typing import Annotated

import pika
from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel

from specvsreality_api.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str = "ok"
    rabbitmq: str = "ok"


def _ping_rabbit(settings: Settings) -> None:
    credentials = pika.PlainCredentials(settings.rabbitmq_username, settings.rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=settings.rabbitmq_host,
        port=settings.rabbitmq_port,
        virtual_host=settings.rabbitmq_virtual_host,
        credentials=credentials,
    )
    connection = pika.BlockingConnection(parameters)
    try:
        connection.channel()
    finally:
        if connection.is_open:
            connection.close()


async def verify_rabbit_reachable(
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    await run_in_threadpool(_ping_rabbit, settings)


@router.get(
    "/health",
    response_model=HealthResponse,
    dependencies=[Depends(verify_rabbit_reachable)],
)
async def get_health() -> HealthResponse:
    return HealthResponse()
