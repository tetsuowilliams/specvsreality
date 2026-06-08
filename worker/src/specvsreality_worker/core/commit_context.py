"""Per-commit context passed across walk stages."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CommitContext:
    repo_id: int
    commit_id: int
    commit_sha: str
    commit_datetime: datetime
    commit_message: str
