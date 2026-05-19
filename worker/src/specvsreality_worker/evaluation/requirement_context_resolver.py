"""Which requirement versions are 'active' at a commit."""

from __future__ import annotations

from specvsreality_repositories.models.repository import Repository
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.repos import (
    RequirementVersionRepo,
    SpecRepo,
    SpecVersionRepo,
)
from specvsreality_worker.domain import CommitRecord


class RequirementContextResolver:
    """Return the requirement versions in scope at a given commit.

    Linear-walk assumption: 'active' is the latest ``SpecVersion`` per
    ``Spec``, regardless of branch ancestry. A genuinely branch-aware
    implementation would walk ``commit_parents`` to find the most recent
    ``SpecVersion`` reachable from ``commit``; the contract of
    :meth:`active_at` is stable so the branch-aware version is a drop-in
    replacement.
    """

    # TODO(temporal): branch-aware ancestor walk via commit_parents (edge case E11).

    def __init__(
        self,
        *,
        spec_repo: SpecRepo,
        spec_version_repo: SpecVersionRepo,
        requirement_version_repo: RequirementVersionRepo,
    ) -> None:
        self._spec_repo = spec_repo
        self._spec_version_repo = spec_version_repo
        self._requirement_version_repo = requirement_version_repo

    def active_at(
        self, *, repository: Repository, commit: CommitRecord
    ) -> list[RequirementVersion]:
        del commit
        out: list[RequirementVersion] = []
        for spec in self._spec_repo.list_for_repo(repository_id=repository.id):
            latest = self._spec_version_repo.latest_for_spec(spec_id=spec.id)
            if latest is None:
                continue
            out.extend(
                self._requirement_version_repo.for_spec_version(
                    spec_version_id=latest.id
                )
            )
        return out
