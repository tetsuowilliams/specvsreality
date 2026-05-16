"""Scan-repo job message."""

from typing import Literal

from pydantic import BaseModel, Field

SCAN_REPO_MESSAGE_TYPE: Literal["scan_repo"] = "scan_repo"


class ScanRepoMessage(BaseModel):
    """Requests the worker to clone and scan one tracked repository."""

    message_type: Literal["scan_repo"] = Field(
        default="scan_repo",
        description="Discriminator for the worker message union.",
    )
    repo_id: str = Field(min_length=1, description="ID of the git_repo row to process.")

