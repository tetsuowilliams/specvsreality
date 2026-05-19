"""Tests for ``RequirementVersionRepo``."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    BlobRepo,
    CommitRepo,
    RequirementRepo,
    RequirementVersionRepo,
    SpecRepo,
    SpecVersionRepo,
)


@pytest.fixture()
def spec_version_id(db_session: Session, repository_id: int) -> int:
    spec = SpecRepo(db_session).get_or_create(
        repository_id=repository_id,
        name="auth",
        spec_path="specs/auth/spec.md",
        plan_path="specs/auth/plan.md",
        tasks_path="specs/auth/tasks.md",
    )
    blob_a = "a" * 40
    blob_b = "b" * 40
    blob_c = "c" * 40
    BlobRepo(db_session).upsert(sha=blob_a, size_bytes=1)
    BlobRepo(db_session).upsert(sha=blob_b, size_bytes=1)
    BlobRepo(db_session).upsert(sha=blob_c, size_bytes=1)
    commit_sha = "1" * 40
    CommitRepo(db_session).insert(
        sha=commit_sha,
        repository_id=repository_id,
        commit_date=datetime.now(UTC),
    )
    sv = SpecVersionRepo(db_session).insert(
        spec_id=spec.id,
        spec_blob_sha=blob_a,
        plan_blob_sha=blob_b,
        tasks_blob_sha=blob_c,
        first_seen_commit=commit_sha,
        first_seen_at=datetime.now(UTC),
    )
    return int(sv.id)


@pytest.fixture()
def requirement_id(db_session: Session, spec_version_id: int) -> int:
    sv = SpecVersionRepo(db_session).get_by_id(spec_version_id)
    assert sv is not None
    req = RequirementRepo(db_session).get_or_create(
        spec_id=sv.spec_id, external_id="FR-001"
    )
    return int(req.id)


def test_insert_then_exists_and_for_spec_version(
    db_session: Session, requirement_id: int, spec_version_id: int
) -> None:
    rv_repo = RequirementVersionRepo(db_session)
    inserted = rv_repo.insert(
        requirement_id=requirement_id,
        spec_version_id=spec_version_id,
        content="Do the thing.",
        content_hash="d" * 40,
        extraction_model="openai:gpt-4o-mini",
        extraction_prompt="prompt-v1",
    )
    assert rv_repo.exists(
        requirement_id=requirement_id, spec_version_id=spec_version_id
    )
    rows = rv_repo.for_spec_version(spec_version_id=spec_version_id)
    assert [r.id for r in rows] == [inserted.id]


def test_latest_for_requirement(
    db_session: Session, requirement_id: int, spec_version_id: int, repository_id: int
) -> None:
    rv_repo = RequirementVersionRepo(db_session)
    first = rv_repo.insert(
        requirement_id=requirement_id,
        spec_version_id=spec_version_id,
        content="v1",
        content_hash="1" * 40,
        extraction_model="m",
        extraction_prompt="p",
    )

    blobs = BlobRepo(db_session)
    blob_d = "d" * 40
    blob_e = "e" * 40
    blob_f = "f" * 40
    blobs.upsert(sha=blob_d, size_bytes=1)
    blobs.upsert(sha=blob_e, size_bytes=1)
    blobs.upsert(sha=blob_f, size_bytes=1)
    commit_sha2 = "2" * 40
    CommitRepo(db_session).insert(
        sha=commit_sha2,
        repository_id=repository_id,
        commit_date=datetime.now(UTC),
    )
    sv = SpecVersionRepo(db_session).get_by_id(spec_version_id)
    assert sv is not None
    sv2 = SpecVersionRepo(db_session).insert(
        spec_id=sv.spec_id,
        spec_blob_sha=blob_d,
        plan_blob_sha=blob_e,
        tasks_blob_sha=blob_f,
        first_seen_commit=commit_sha2,
        first_seen_at=datetime.now(UTC),
    )
    second = rv_repo.insert(
        requirement_id=requirement_id,
        spec_version_id=sv2.id,
        content="v2",
        content_hash="2" * 40,
        extraction_model="m",
        extraction_prompt="p",
    )

    latest = rv_repo.latest_for_requirement(requirement_id=requirement_id)
    assert latest is not None
    assert latest.id == second.id
    assert first.id != second.id
