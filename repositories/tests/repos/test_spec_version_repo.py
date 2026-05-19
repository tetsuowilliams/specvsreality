"""Tests for ``SpecVersionRepo``."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    BlobRepo,
    CommitRepo,
    SpecRepo,
    SpecVersionRepo,
)


@pytest.fixture()
def spec_id(db_session: Session, repository_id: int) -> int:
    spec = SpecRepo(db_session).get_or_create(
        repository_id=repository_id,
        name="auth",
        spec_path="specs/auth/spec.md",
        plan_path="specs/auth/plan.md",
        tasks_path="specs/auth/tasks.md",
    )
    return int(spec.id)


@pytest.fixture()
def commit_sha(db_session: Session, repository_id: int) -> str:
    sha = "c" * 40
    CommitRepo(db_session).insert(
        sha=sha, repository_id=repository_id, commit_date=datetime.now(UTC)
    )
    return sha


@pytest.fixture()
def triplet_blobs(db_session: Session) -> tuple[str, str, str]:
    blobs = BlobRepo(db_session)
    spec_blob = "a" * 40
    plan_blob = "b" * 40
    tasks_blob = "c" * 40
    blobs.upsert(sha=spec_blob, size_bytes=1)
    blobs.upsert(sha=plan_blob, size_bytes=1)
    blobs.upsert(sha=tasks_blob, size_bytes=1)
    return spec_blob, plan_blob, tasks_blob


def test_insert_and_find_by_triplet(
    db_session: Session,
    spec_id: int,
    commit_sha: str,
    triplet_blobs: tuple[str, str, str],
) -> None:
    spec_blob, plan_blob, tasks_blob = triplet_blobs
    versions = SpecVersionRepo(db_session)
    inserted = versions.insert(
        spec_id=spec_id,
        spec_blob_sha=spec_blob,
        plan_blob_sha=plan_blob,
        tasks_blob_sha=tasks_blob,
        first_seen_commit=commit_sha,
        first_seen_at=datetime.now(UTC),
    )

    found = versions.find_by_triplet(
        spec_id=spec_id,
        spec_blob_sha=spec_blob,
        plan_blob_sha=plan_blob,
        tasks_blob_sha=tasks_blob,
    )

    assert found is not None
    assert found.id == inserted.id


def test_insert_and_find_by_triplet_with_partial_triplet(
    db_session: Session,
    spec_id: int,
    commit_sha: str,
    triplet_blobs: tuple[str, str, str],
) -> None:
    """spec.md only at first; plan/tasks NULL must round-trip through the repo."""
    spec_blob, _, _ = triplet_blobs
    versions = SpecVersionRepo(db_session)
    inserted = versions.insert(
        spec_id=spec_id,
        spec_blob_sha=spec_blob,
        plan_blob_sha=None,
        tasks_blob_sha=None,
        first_seen_commit=commit_sha,
        first_seen_at=datetime.now(UTC),
    )

    found = versions.find_by_triplet(
        spec_id=spec_id,
        spec_blob_sha=spec_blob,
        plan_blob_sha=None,
        tasks_blob_sha=None,
    )

    assert found is not None
    assert found.id == inserted.id
    assert found.plan_blob_sha is None
    assert found.tasks_blob_sha is None


def test_partial_triplet_does_not_match_full_triplet(
    db_session: Session,
    spec_id: int,
    commit_sha: str,
    triplet_blobs: tuple[str, str, str],
) -> None:
    """Adding plan.md later must yield a distinct row, not collide via NULL."""
    spec_blob, plan_blob, tasks_blob = triplet_blobs
    versions = SpecVersionRepo(db_session)
    versions.insert(
        spec_id=spec_id,
        spec_blob_sha=spec_blob,
        plan_blob_sha=None,
        tasks_blob_sha=None,
        first_seen_commit=commit_sha,
        first_seen_at=datetime.now(UTC),
    )

    assert (
        versions.find_by_triplet(
            spec_id=spec_id,
            spec_blob_sha=spec_blob,
            plan_blob_sha=plan_blob,
            tasks_blob_sha=tasks_blob,
        )
        is None
    )


def test_latest_for_spec_picks_most_recent(
    db_session: Session,
    spec_id: int,
    repository_id: int,
    triplet_blobs: tuple[str, str, str],
) -> None:
    spec_blob, plan_blob, tasks_blob = triplet_blobs
    versions = SpecVersionRepo(db_session)
    commits = CommitRepo(db_session)
    blobs = BlobRepo(db_session)
    base = datetime.now(UTC)

    early_commit = "1" * 40
    later_commit = "2" * 40
    commits.insert(sha=early_commit, repository_id=repository_id, commit_date=base)
    commits.insert(
        sha=later_commit,
        repository_id=repository_id,
        commit_date=base + timedelta(days=1),
    )

    plan_blob_v2 = "9" * 40
    blobs.upsert(sha=plan_blob_v2, size_bytes=1)

    versions.insert(
        spec_id=spec_id,
        spec_blob_sha=spec_blob,
        plan_blob_sha=plan_blob,
        tasks_blob_sha=tasks_blob,
        first_seen_commit=early_commit,
        first_seen_at=base,
    )
    later = versions.insert(
        spec_id=spec_id,
        spec_blob_sha=spec_blob,
        plan_blob_sha=plan_blob_v2,
        tasks_blob_sha=tasks_blob,
        first_seen_commit=later_commit,
        first_seen_at=base + timedelta(days=1),
    )

    latest = versions.latest_for_spec(spec_id=spec_id)
    assert latest is not None
    assert latest.id == later.id
