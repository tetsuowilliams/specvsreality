"""Hello-world job message (smoke test / plumbing verification)."""

from typing import Literal

from pydantic import BaseModel, Field

HELLO_WORLD_MESSAGE_TYPE: Literal["hello_world"] = "hello_world"


class HelloWorldMessage(BaseModel):
    """A minimal message used to validate queue → parse → dispatch."""

    message_type: Literal["hello_world"] = Field(
        default="hello_world",
        description="Discriminator for the worker message union.",
    )
    name: str = Field(min_length=1, description="Name to greet.")
