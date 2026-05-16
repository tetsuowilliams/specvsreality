"""Scan repository trees for files matching glob patterns."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import PurePosixPath

from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.git_adapter import GitAdapter


class TreeScan:
    """Utility for listing files in a commit matching one or more globs."""

    def __init__(self, *, git_adapter: GitAdapter) -> None:
        self._git_adapter = git_adapter

    def scan_tree(self, commit: CommitContext, globs: Sequence[str]) -> list[str]:
        """
        Return all file paths at ``commit`` that match any of the provided globs.

        Globs are interpreted using ``PurePosixPath.match`` against POSIX-style
        relative paths (e.g. ``"src/**/*.py"`` or ``"README.md"``).
        """
        if not globs:
            return []

        files = self._git_adapter.list_files_at_commit(commit.commit_sha)

        # Preserve order from git while de-duplicating.
        seen: set[str] = set()
        matches: list[str] = []

        for path in files:
            for pattern in globs:
                if self.is_glob_match(pattern=pattern, file_path=path) and path not in seen:
                    seen.add(path)
                    matches.append(path)
                    break

        return matches

    def is_glob_match(self, *, pattern: str, file_path: str) -> bool:
        """Return True when ``file_path`` matches ``pattern``."""
        return PurePosixPath(file_path).match(pattern)

