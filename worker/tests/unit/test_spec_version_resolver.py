"""Tests for ``SpecVersionResolver``."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from specvsreality_repositories.models.spec import Spec
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_worker.domain import CommitRecord
from specvsreality_worker.spec import SpecVersionResolver


def _spec(id_: int = 1) -> Spec:
    return Spec(
        id=id_,
        repository_id=10,
        name="auth",
        spec_path="specs/auth/spec.md",
        plan_path="specs/auth/plan.md",
        tasks_path="specs/auth/tasks.md",
    )


def _commit(sha: str = "1" * 40) -> CommitRecord:
    return CommitRecord(
        sha=sha, repository_id=10, commit_date=datetime.now(UTC)
    )


def test_returns_none_when_spec_md_missing() -> None:
    """Anchor is ``spec.md``: if it is gone, the spec doesn't exist at this commit."""
    spec_version_repo = MagicMock()
    commit_file_repo = MagicMock()
    commit_file_repo.blob_at.side_effect = [None, "b" * 40, "c" * 40]

    resolver = SpecVersionResolver(
        spec_version_repo=spec_version_repo, commit_file_repo=commit_file_repo
    )
    assert resolver.resolve(spec=_spec(), commit=_commit()) is None
    spec_version_repo.find_by_triplet.assert_not_called()


def test_returns_existing_resolution_when_triplet_known() -> None:
    spec_version_repo = MagicMock()
    commit_file_repo = MagicMock()
    commit_file_repo.blob_at.side_effect = ["a" * 40, "b" * 40, "c" * 40]
    existing = MagicMock(spec=SpecVersion)
    spec_version_repo.find_by_triplet.return_value = existing

    resolver = SpecVersionResolver(
        spec_version_repo=spec_version_repo, commit_file_repo=commit_file_repo
    )
    out = resolver.resolve(spec=_spec(), commit=_commit())
    assert out is not None
    assert out.spec_version is existing
    assert out.is_new is False
    spec_version_repo.insert.assert_not_called()


def test_inserts_when_triplet_is_new() -> None:
    spec_version_repo = MagicMock()
    commit_file_repo = MagicMock()
    commit_file_repo.blob_at.side_effect = ["a" * 40, "b" * 40, "c" * 40]
    spec_version_repo.find_by_triplet.return_value = None
    inserted = MagicMock(spec=SpecVersion)
    spec_version_repo.insert.return_value = inserted

    resolver = SpecVersionResolver(
        spec_version_repo=spec_version_repo, commit_file_repo=commit_file_repo
    )
    out = resolver.resolve(spec=_spec(), commit=_commit("9" * 40))
    assert out is not None
    assert out.spec_version is inserted
    assert out.is_new is True
    insert_kwargs = spec_version_repo.insert.call_args.kwargs
    assert insert_kwargs["spec_blob_sha"] == "a" * 40
    assert insert_kwargs["plan_blob_sha"] == "b" * 40
    assert insert_kwargs["tasks_blob_sha"] == "c" * 40
    assert insert_kwargs["first_seen_commit"] == "9" * 40


def test_resolves_when_only_spec_md_present() -> None:
    """spec-kit specs typically land ``spec.md`` first; plan/tasks may be missing."""
    spec_version_repo = MagicMock()
    commit_file_repo = MagicMock()
    commit_file_repo.blob_at.side_effect = ["a" * 40, None, None]
    spec_version_repo.find_by_triplet.return_value = None
    inserted = MagicMock(spec=SpecVersion)
    spec_version_repo.insert.return_value = inserted

    resolver = SpecVersionResolver(
        spec_version_repo=spec_version_repo, commit_file_repo=commit_file_repo
    )
    out = resolver.resolve(spec=_spec(), commit=_commit("7" * 40))

    assert out is not None
    assert out.is_new is True
    find_kwargs = spec_version_repo.find_by_triplet.call_args.kwargs
    assert find_kwargs["plan_blob_sha"] is None
    assert find_kwargs["tasks_blob_sha"] is None
    insert_kwargs = spec_version_repo.insert.call_args.kwargs
    assert insert_kwargs["spec_blob_sha"] == "a" * 40
    assert insert_kwargs["plan_blob_sha"] is None
    assert insert_kwargs["tasks_blob_sha"] is None


def test_partial_triplet_dedups_against_existing_partial_row() -> None:
    """Adding plan/tasks later must produce a *new* version, not collide."""
    spec_version_repo = MagicMock()
    commit_file_repo = MagicMock()
    commit_file_repo.blob_at.side_effect = ["a" * 40, "b" * 40, None]
    spec_version_repo.find_by_triplet.return_value = None
    inserted = MagicMock(spec=SpecVersion)
    spec_version_repo.insert.return_value = inserted

    resolver = SpecVersionResolver(
        spec_version_repo=spec_version_repo, commit_file_repo=commit_file_repo
    )
    resolver.resolve(spec=_spec(), commit=_commit("8" * 40))

    find_kwargs = spec_version_repo.find_by_triplet.call_args.kwargs
    assert find_kwargs["plan_blob_sha"] == "b" * 40
    assert find_kwargs["tasks_blob_sha"] is None
