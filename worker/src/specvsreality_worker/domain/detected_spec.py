"""Spec triplet discovered from a commit's tree, prior to persistence."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectedSpec:
    """A spec-kit candidate (name, spec/plan/tasks paths) found by ``SpecDetector``.

    A spec is only persisted as a ``Spec`` row once we have a fully resolvable
    triplet for at least one commit; ``DetectedSpec`` is the pre-DB representation.
    """

    name: str
    spec_path: str
    plan_path: str
    tasks_path: str
