"""Hello-world → queue (smoke / plumbing)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from specvsreality_api.config import Settings, get_settings
from specvsreality_api.messaging.publisher import MessagePublisher, PikaMessagePublisher
from specvsreality_messages import HelloWorldMessage

router = APIRouter(tags=["hello-world"])


class HelloWorldRequest(BaseModel):
    name: str = Field(min_length=1, max_length=256)


class HelloWorldResponse(BaseModel):
    queued: bool = True


def get_publisher() -> MessagePublisher:
    return PikaMessagePublisher()


@router.post("/hello-world", response_model=HelloWorldResponse)
async def post_hello_world(
    body: HelloWorldRequest,
    settings: Annotated[Settings, Depends(get_settings)],
    publisher: Annotated[MessagePublisher, Depends(get_publisher)],
) -> HelloWorldResponse:
    message = HelloWorldMessage(name=body.name)
    await publisher.publish(message.model_dump_json().encode("utf-8"), settings)
    return HelloWorldResponse()
