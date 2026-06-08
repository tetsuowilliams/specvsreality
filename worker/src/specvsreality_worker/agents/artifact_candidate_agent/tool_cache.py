"""In-memory cache for repository tool results within a single commit evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CommitToolCache:
    """Stores tool outputs keyed by tool name and arguments (commit-scoped)."""

    _entries: dict[tuple[Any, ...], Any] = field(default_factory=dict)

    def has(self, key: tuple[Any, ...]) -> bool:
        return key in self._entries

    def get(self, key: tuple[Any, ...]) -> Any:
        return self._entries[key]

    def put(self, key: tuple[Any, ...], value: Any) -> None:
        self._entries[key] = value
