"""Result of resolving a (Spec, commit) pair to a SpecVersion row."""

from __future__ import annotations

from dataclasses import dataclass

from specvsreality_repositories.models.spec_version import SpecVersion


@dataclass(frozen=True)
class SpecVersionResolution:
    """A persisted ``SpecVersion`` with a flag for whether this call created it.

    Callers use ``is_new`` to decide whether downstream LLM extraction is needed.
    """

    spec_version: SpecVersion
    is_new: bool
