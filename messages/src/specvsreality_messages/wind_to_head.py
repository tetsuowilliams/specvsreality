"""Wind-to-head job message."""

from typing import Literal

from pydantic import BaseModel, Field

WIND_TO_HEAD_MESSAGE_TYPE: Literal["wind_to_head"] = "wind_to_head"


class WindToHeadMessage(BaseModel):
    """Requests the worker to pull and walk commits from cursor to branch tip."""

    message_type: Literal["wind_to_head"] = Field(
        default="wind_to_head",
        description="Discriminator for the worker message union.",
    )
    repo_id: str = Field(min_length=1, description="ID of the git_repo row to process.")
