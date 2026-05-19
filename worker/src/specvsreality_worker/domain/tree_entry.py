"""Single file in a commit's tree."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TreeEntry:
    """A path / blob / mode tuple at one commit."""

    path: str
    blob_sha: str
    size_bytes: int | None = None
    mode: str | None = None
