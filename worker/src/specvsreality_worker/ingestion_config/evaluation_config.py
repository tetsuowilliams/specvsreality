"""Configuration for implementation-evaluation LLM calls."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from specvsreality_worker.domain import TreeEntry
from specvsreality_worker.ingestion_config.spec_pattern_config import SpecPatternConfig


@dataclass(frozen=True)
class EvaluationConfig:
    """Identifies the model + prompt used by :class:`ImplementationEvaluator`.

    ``model_version`` and ``prompt_version`` are stamped on every
    :class:`ImplementationClaim` row and are the keys that
    :meth:`ImplementationClaimRepo.has_claim` uses for dedup.

    ``spec_filename`` triplet identifies which paths in a tree should be
    excluded from the code-evaluation set.
    """

    model_version: str
    prompt_version: str
    prompt: str
    spec_pattern: SpecPatternConfig

    def is_spec_file(self, path: str) -> bool:
        basename = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
        return basename in {
            self.spec_pattern.spec_filename.lower(),
            self.spec_pattern.plan_filename.lower(),
            self.spec_pattern.tasks_filename.lower(),
        }

    def spec_file_paths(self, tree: Iterable[TreeEntry]) -> set[str]:
        return {entry.path for entry in tree if self.is_spec_file(entry.path)}
