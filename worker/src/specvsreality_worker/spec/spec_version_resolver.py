"""Resolve a (Spec, commit) pair to a SpecVersion, deduping by triplet."""

from __future__ import annotations

from specvsreality_repositories.models.spec import Spec
from specvsreality_repositories.repos import CommitFileRepo, SpecVersionRepo
from specvsreality_worker.domain import (
    CommitRecord,
    SpecFileTriplet,
    SpecVersionResolution,
)


class SpecVersionResolver:
    """Map a ``(Spec, CommitRecord)`` to a persisted ``SpecVersion``.

    Anchors on ``spec.md`` -- if the spec file itself is absent at the commit,
    ``resolve`` returns ``None`` and the caller skips this spec for this
    commit. ``plan.md`` / ``tasks.md`` are optional: their absence is
    represented by ``None`` in the triplet so spec-kit specs that land
    ``spec.md`` first still produce a row at the moment they appear.

    Dedup uses the unique ``(spec_id, spec_blob, plan_blob, tasks_blob)``
    constraint with ``NULLS NOT DISTINCT`` -- the same partial triplet
    across different commits resolves to the same ``SpecVersion`` row.
    """

    def __init__(
        self,
        *,
        spec_version_repo: SpecVersionRepo,
        commit_file_repo: CommitFileRepo,
    ) -> None:
        self._spec_version_repo = spec_version_repo
        self._commit_file_repo = commit_file_repo

    def resolve(
        self, *, spec: Spec, commit: CommitRecord
    ) -> SpecVersionResolution | None:
        triplet = self._build_triplet(spec=spec, commit=commit)
        if triplet is None:
            return None

        existing = self._spec_version_repo.find_by_triplet(
            spec_id=spec.id,
            spec_blob_sha=triplet.spec_blob_sha,
            plan_blob_sha=triplet.plan_blob_sha,
            tasks_blob_sha=triplet.tasks_blob_sha,
        )
        if existing is not None:
            return SpecVersionResolution(spec_version=existing, is_new=False)

        created = self._spec_version_repo.insert(
            spec_id=spec.id,
            spec_blob_sha=triplet.spec_blob_sha,
            plan_blob_sha=triplet.plan_blob_sha,
            tasks_blob_sha=triplet.tasks_blob_sha,
            first_seen_commit=commit.sha,
            first_seen_at=commit.commit_date,
        )
        return SpecVersionResolution(spec_version=created, is_new=True)

    def _build_triplet(
        self, *, spec: Spec, commit: CommitRecord
    ) -> SpecFileTriplet | None:
        spec_sha = self._commit_file_repo.blob_at(
            commit_sha=commit.sha, path=spec.spec_path
        )
        if spec_sha is None:
            return None
        return SpecFileTriplet(
            spec_blob_sha=spec_sha,
            plan_blob_sha=self._commit_file_repo.blob_at(
                commit_sha=commit.sha, path=spec.plan_path
            ),
            tasks_blob_sha=self._commit_file_repo.blob_at(
                commit_sha=commit.sha, path=spec.tasks_path
            ),
        )
