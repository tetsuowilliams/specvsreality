"""Plain commit + parent edge value types from the git layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class ParentRef:
    """A single parent edge of a commit (sha + position in the parent list)."""

    parent_sha: str
    parent_order: int


@dataclass(frozen=True)
class CommitRecord:
    """A git commit as returned by ``GitClient.iter_commits``.

    Holds only what the ingestion pipeline persists in ``commits`` /
    ``commit_parents``. ``repository_id`` is set by the caller (the git client
    is repo-scoped).
    """

    sha: str
    repository_id: int
    commit_date: datetime
    parent_shas: list[ParentRef] = field(default_factory=list)
    author_name: str | None = None
    author_email: str | None = None
    author_date: datetime | None = None
    committer_name: str | None = None
    committer_email: str | None = None
    message: str | None = None
