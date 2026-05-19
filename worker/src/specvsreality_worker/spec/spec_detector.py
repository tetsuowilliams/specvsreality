"""Discover spec-kit specs in a commit's tree by file pattern."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import PurePosixPath

from specvsreality_worker.domain import DetectedSpec, TreeEntry
from specvsreality_worker.ingestion_config import SpecPatternConfig


class SpecDetector:
    """Pure function over a tree listing.

    A spec is identified by the presence of a configured ``spec.md`` file under
    a parent folder. The parent folder name is the spec ``name``. Sibling paths
    for ``plan.md`` / ``tasks.md`` are computed but not required to exist at
    detection time -- ``SpecVersionResolver`` is responsible for confirming the
    full triplet at a specific commit.
    """

    def __init__(self, *, config: SpecPatternConfig) -> None:
        self._config = config

    def detect(self, tree: Iterable[TreeEntry]) -> list[DetectedSpec]:
        spec_filename = self._config.spec_filename.lower()
        out: list[DetectedSpec] = []
        seen: set[tuple[int, str]] = set()
        for entry in tree:
            posix = entry.path.replace("\\", "/")
            path = PurePosixPath(posix) 
            if path.name.lower() != spec_filename:
                continue
            parent = path.parent
            if str(parent) in ("", "."):
                continue
            name = parent.name
            if not name:
                continue
            key = (len(parent.parts), str(parent))
            if key in seen:
                continue
            seen.add(key)
            out.append(
                DetectedSpec(
                    name=name,
                    spec_path=str(parent / self._config.spec_filename),
                    plan_path=str(parent / self._config.plan_filename),
                    tasks_path=str(parent / self._config.tasks_filename),
                )
            )
        return out
