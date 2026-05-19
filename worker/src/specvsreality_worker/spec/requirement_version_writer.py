"""Persist one extracted requirement, applying the (req, spec_version) idempotency check."""

from __future__ import annotations

from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos import (
    RequirementRepo,
    RequirementVersionRepo,
)
from specvsreality_worker.domain import ExtractedRequirement
from specvsreality_worker.support import HashUtil


class RequirementVersionWriter:
    """Write an :class:`ExtractedRequirement` to ``requirements`` + ``requirement_versions``.

    The unique ``(requirement_id, spec_version_id)`` constraint guarantees that
    re-running extraction for the same spec version returns the existing row
    rather than creating a duplicate. Callers should treat the returned row as
    authoritative regardless of whether it was just inserted.
    """

    def __init__(
        self,
        *,
        requirement_repo: RequirementRepo,
        requirement_version_repo: RequirementVersionRepo,
        hash_util: HashUtil,
    ) -> None:
        self._requirement_repo = requirement_repo
        self._requirement_version_repo = requirement_version_repo
        self._hash = hash_util

    def write(
        self,
        *,
        spec_version: SpecVersion,
        extracted: ExtractedRequirement,
        extraction_model: str,
        extraction_prompt: str,
    ) -> RequirementVersion:
        requirement = self._requirement_repo.get_or_create(
            spec_id=spec_version.spec_id,
            external_id=extracted.external_id,
        )
        existing = self._requirement_version_repo.get_for_pair(
            requirement_id=requirement.id,
            spec_version_id=spec_version.id,
        )
        if existing is not None:
            return existing

        return self._requirement_version_repo.insert(
            requirement_id=requirement.id,
            spec_version_id=spec_version.id,
            content=extracted.content,
            content_hash=self._hash.sha1_hex(extracted.content),
            extraction_model=extraction_model,
            extraction_prompt=extraction_prompt,
            path_globs=list(extracted.path_globs),
        )
