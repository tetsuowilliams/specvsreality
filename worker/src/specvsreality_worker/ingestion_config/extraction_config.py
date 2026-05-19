"""Configuration for requirement extraction LLM calls."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractionConfig:
    """Identifies the model + prompt used by :class:`RequirementExtractor`.

    ``extraction_prompt`` is the verbatim prompt body persisted on each
    ``requirement_versions`` row; ``extraction_prompt_version`` is the short
    version stamp used for indexing / dedup queries.
    """

    extraction_model: str
    extraction_prompt: str
    extraction_prompt_version: str
