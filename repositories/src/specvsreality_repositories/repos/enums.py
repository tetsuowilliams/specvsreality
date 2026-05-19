"""Persistence-layer enumerations."""

from __future__ import annotations

from enum import StrEnum


class Verdict(StrEnum):
    """Outcome of an LLM judgment that a blob implements a requirement version."""

    IMPLEMENTS = "implements"
    DOES_NOT_IMPLEMENT = "does_not_implement"
    PARTIAL = "partial"
    UNCLEAR = "unclear"
