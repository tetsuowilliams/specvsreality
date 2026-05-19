"""Tests for ``RequirementRepo``."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import RequirementRepo, SpecRepo


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


def test_get_or_create_is_idempotent(db_session: Session, spec_id: int) -> None:
    repo = RequirementRepo(db_session)
    first = repo.get_or_create(spec_id=spec_id, external_id="FR-001")
    second = repo.get_or_create(spec_id=spec_id, external_id="FR-001")
    assert first.id == second.id


def test_list_for_spec(db_session: Session, spec_id: int) -> None:
    repo = RequirementRepo(db_session)
    repo.get_or_create(spec_id=spec_id, external_id="FR-002")
    repo.get_or_create(spec_id=spec_id, external_id="FR-001")
    rows = repo.list_for_spec(spec_id=spec_id)
    assert [r.external_id for r in rows] == ["FR-001", "FR-002"]
