"""Configuration for spec-kit detection patterns."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecPatternConfig:
    """Filenames and parent-folder rules used by :class:`SpecDetector`.

    The default matches spec-kit's `<parent>/spec.md` + sibling `plan.md` /
    `tasks.md` convention. The detected ``name`` is the parent directory.
    """

    spec_filename: str = "spec.md"
    plan_filename: str = "plan.md"
    tasks_filename: str = "tasks.md"
