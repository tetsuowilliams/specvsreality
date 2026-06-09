"""Init-repo job message."""

from typing import Literal

from pydantic import BaseModel, Field

INIT_REPO_MESSAGE_TYPE: Literal["init_repo"] = "init_repo"


class InitRepoMessage(BaseModel):
    """Requests the worker to clone a tracked repository and seed its cursor."""

    message_type: Literal["init_repo"] = Field(
        default="init_repo",
        description="Discriminator for the worker message union.",
    )
    repo_id: str = Field(min_length=1, description="ID of the git_repo row to process.")
