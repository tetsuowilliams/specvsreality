"""Spec-scan job message."""

from typing import Literal

from pydantic import BaseModel, Field

SPEC_SCAN_MESSAGE_TYPE: Literal["spec_scan"] = "spec_scan"


class SpecScanMessage(BaseModel):
    """Requests the worker to extract and evaluate one spec folder at a commit."""

    message_type: Literal["spec_scan"] = Field(
        default="spec_scan",
        description="Discriminator for the worker message union.",
    )
    repo_id: str = Field(min_length=1, description="ID of the git_repo row.")
    commit_id: int = Field(ge=1, description="DB primary key of the commit row.")
    spec_folder: str = Field(min_length=1, description="Spec directory path, e.g. specs/my-feature.")
    extract_spec: bool = Field(
        default=True,
        description=(
            "When true, run spec extraction for this commit if the spec changed. "
            "When false, load the latest spec version at or before this commit from the DB."
        ),
    )
