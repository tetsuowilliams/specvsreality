"""Per-commit step: detect specs, resolve versions, extract new requirements."""

from __future__ import annotations

import logging

from specvsreality_repositories.models.repository import Repository
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.repos import SpecRepo
from specvsreality_worker.domain import CommitRecord, TreeEntry
from specvsreality_worker.spec import (
    RequirementExtractor,
    SpecDetector,
    SpecVersionResolver,
)

logger = logging.getLogger(__name__)


class SpecSyncStep:
    """For one commit: discover specs, dedup spec versions, run extraction.

    Returns the list of newly created :class:`RequirementVersion` rows so the
    caller can run retroactive backfill against them.
    """

    def __init__(
        self,
        *,
        spec_detector: SpecDetector,
        spec_repo: SpecRepo,
        spec_version_resolver: SpecVersionResolver,
        requirement_extractor: RequirementExtractor,
    ) -> None:
        self._detector = spec_detector
        self._spec_repo = spec_repo
        self._resolver = spec_version_resolver
        self._extractor = requirement_extractor

    def process(
        self,
        *,
        repository: Repository,
        commit: CommitRecord,
        tree: list[TreeEntry],
    ) -> list[RequirementVersion]:
        new_versions: list[RequirementVersion] = []
        for detected in self._detector.detect(tree):
            spec = self._spec_repo.get_or_create(
                repository_id=repository.id,
                name=detected.name,
                spec_path=detected.spec_path,
                plan_path=detected.plan_path,
                tasks_path=detected.tasks_path,
            )
            resolution = self._resolver.resolve(spec=spec, commit=commit)
            if resolution is None:
                # spec.md missing at the commit: only happens if detector and
                # commit_files disagree (deletion races, manual data edits).
                logger.warning(
                    "spec %r anchor %s missing at commit %s -- skipping",
                    detected.name,
                    spec.spec_path,
                    commit.sha[:7],
                )
                continue
            if not resolution.is_new:
                continue
            new_versions.extend(
                self._extractor.extract(spec_version=resolution.spec_version)
            )
        return new_versions
