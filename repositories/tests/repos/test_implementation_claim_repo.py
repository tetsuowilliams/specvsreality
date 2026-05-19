"""Tests for ``ImplementationClaimRepo``."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    BlobRepo,
    CommitFileRepo,
    CommitRepo,
    ImplementationClaimRepo,
    RequirementRepo,
    RequirementVersionRepo,
    SpecRepo,
    SpecVersionRepo,
    Verdict,
)


@pytest.fixture()
def fixture_world(db_session: Session, repository_id: int) -> dict[str, int | str]:
    """Build a minimal commit / spec / requirement_version / blob graph."""
    blobs = BlobRepo(db_session)
    blob_spec = "a" * 40
    blob_plan = "b" * 40
    blob_tasks = "c" * 40
    blob_code = "d" * 40
    for sha in (blob_spec, blob_plan, blob_tasks, blob_code):
        blobs.upsert(sha=sha, size_bytes=1)

    commit_sha = "1" * 40
    CommitRepo(db_session).insert(
        sha=commit_sha,
        repository_id=repository_id,
        commit_date=datetime.now(UTC),
    )
    CommitFileRepo(db_session).insert_many(
        commit_sha=commit_sha,
        entries=[("src/app.py", blob_code, None)],
    )

    spec = SpecRepo(db_session).get_or_create(
        repository_id=repository_id,
        name="auth",
        spec_path="specs/auth/spec.md",
        plan_path="specs/auth/plan.md",
        tasks_path="specs/auth/tasks.md",
    )
    sv = SpecVersionRepo(db_session).insert(
        spec_id=spec.id,
        spec_blob_sha=blob_spec,
        plan_blob_sha=blob_plan,
        tasks_blob_sha=blob_tasks,
        first_seen_commit=commit_sha,
        first_seen_at=datetime.now(UTC),
    )
    req = RequirementRepo(db_session).get_or_create(
        spec_id=spec.id, external_id="FR-001"
    )
    rv = RequirementVersionRepo(db_session).insert(
        requirement_id=req.id,
        spec_version_id=sv.id,
        content="impl this",
        content_hash="9" * 40,
        extraction_model="m",
        extraction_prompt="p",
    )
    return {
        "rv_id": int(rv.id),
        "blob_code": blob_code,
        "commit_sha": commit_sha,
    }


def test_insert_and_has_claim(db_session: Session, fixture_world: dict) -> None:
    claims = ImplementationClaimRepo(db_session)
    rv_id = int(fixture_world["rv_id"])
    blob = str(fixture_world["blob_code"])

    assert (
        claims.has_claim(
            requirement_version_id=rv_id,
            blob_sha=blob,
            model_version="m1",
            prompt_version="p1",
        )
        is False
    )
    claims.insert(
        requirement_version_id=rv_id,
        blob_sha=blob,
        verdict=Verdict.IMPLEMENTS.value,
        confidence=0.9,
        model_version="m1",
        prompt_version="p1",
        reasoning="looks good",
    )
    assert claims.has_claim(
        requirement_version_id=rv_id,
        blob_sha=blob,
        model_version="m1",
        prompt_version="p1",
    )


def test_has_claim_filters_by_model_and_prompt(
    db_session: Session, fixture_world: dict
) -> None:
    claims = ImplementationClaimRepo(db_session)
    rv_id = int(fixture_world["rv_id"])
    blob = str(fixture_world["blob_code"])
    claims.insert(
        requirement_version_id=rv_id,
        blob_sha=blob,
        verdict=Verdict.IMPLEMENTS.value,
        confidence=None,
        model_version="m1",
        prompt_version="p1",
        reasoning=None,
    )
    assert (
        claims.has_claim(
            requirement_version_id=rv_id,
            blob_sha=blob,
            model_version="m2",
            prompt_version="p1",
        )
        is False
    )


def test_current_for_commit_returns_latest_per_blob(
    db_session: Session, fixture_world: dict
) -> None:
    claims = ImplementationClaimRepo(db_session)
    rv_id = int(fixture_world["rv_id"])
    blob = str(fixture_world["blob_code"])
    commit_sha = str(fixture_world["commit_sha"])

    claims.insert(
        requirement_version_id=rv_id,
        blob_sha=blob,
        verdict=Verdict.PARTIAL.value,
        confidence=0.4,
        model_version="m1",
        prompt_version="p1",
        reasoning="r1",
    )
    latest = claims.insert(
        requirement_version_id=rv_id,
        blob_sha=blob,
        verdict=Verdict.IMPLEMENTS.value,
        confidence=0.9,
        model_version="m2",
        prompt_version="p1",
        reasoning="r2",
    )

    rows = claims.current_for_commit(
        commit_sha=commit_sha, requirement_version_id=rv_id
    )
    assert [r.id for r in rows] == [latest.id]
