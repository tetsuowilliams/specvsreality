"""Detect spec files and build Spec models from raw content."""

from __future__ import annotations

from pathlib import PurePosixPath

from specvsreality_worker.models.spec import Spec

_SPEC_BASENAMES = frozenset({"SPEC.md", "SPEC.yaml", "SPEC.yml"})
_SPEC_SUFFIXES = (".spec.md", ".spec.yaml", ".spec.yml")


class SpecAnalyser:
    """Detect spec paths and construct :class:`Spec` instances from file bodies."""

    def is_spec_path(self, path: str) -> bool:
        """Return True if ``path`` matches configured spec filename rules (POSIX-style)."""
        normalized = path.replace("\\", "/").strip("/")
        if not normalized:
            return False
        name = PurePosixPath(normalized).name
        if name in _SPEC_BASENAMES:
            return True
        return any(name.endswith(suffix) for suffix in _SPEC_SUFFIXES)

    def build_spec(self, *, filepath: str, content: str) -> Spec:
        """Build a :class:`Spec` from repo-relative path and file body."""
        normalized = filepath.replace("\\", "/").strip("/")
        if not normalized:
            raise ValueError("filepath must be non-empty")
        filename = PurePosixPath(normalized).name
        return Spec(filename=filename, filepath=normalized, content=content)
