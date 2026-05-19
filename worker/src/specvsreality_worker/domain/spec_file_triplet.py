"""Blob SHAs identifying one immutable spec snapshot."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecFileTriplet:
    """The (spec, plan, tasks) blob trio that uniquely identifies a spec version.

    Only ``spec_blob_sha`` is required: ``plan_blob_sha`` and ``tasks_blob_sha``
    may be ``None`` for spec-kit specs that have not yet had ``plan.md`` /
    ``tasks.md`` authored. The triplet (with ``None`` slots) is the dedup key.
    """

    spec_blob_sha: str
    plan_blob_sha: str | None
    tasks_blob_sha: str | None
