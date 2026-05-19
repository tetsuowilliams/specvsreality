"""LLM-extracted requirement, pre-persistence."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ExtractedRequirement:
    """An ``external_id`` + ``content`` pair returned by the spec extraction agent.

    ``path_globs`` carries the LLM's hint about where this requirement is likely
    implemented; it is persisted alongside the requirement version so that the
    candidate-filter step at evaluation time can short-circuit obviously
    irrelevant blobs without an LLM call.
    """

    external_id: str
    content: str
    path_globs: tuple[str, ...] = field(default_factory=tuple)
