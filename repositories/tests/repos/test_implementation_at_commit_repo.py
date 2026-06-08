"""Tests for `ImplementationAtCommitRepo`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.repos import (
    create_implementation_at_commit_repo,
    create_spec_item_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus

_DT = datetime(2026, 1, 15, tzinfo=UTC)


def _make_spec_item(db_session: Session, *, git_repo_id: int, commit_id: int) -> int:
    spec = create_spec_repo(db_session).add(paper_id="0001-eval", repo_id=git_repo_id)
    version = create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        commit_id=commit_id,
        title="T",
        summary="S",
        spec_md="# s",
        tasks_md=None,
        plan_md=None,
        created_at=_DT,
        status=VersionStatus.ACTIVE,
    )
    item = create_spec_item_repo(db_session).add(
        spec_version_id=version.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="text",
        source_quote="q",
        importance=SpecItemImportance.MUST,
        success_criteria=[],
        failure_criteria=[],
    )
    return item.id


def test_upsert_evaluation_persists_and_updates(
    db_session: Session,
    git_repo_id: int,
    commit_id: int,
) -> None:
    item_id = _make_spec_item(db_session, git_repo_id=git_repo_id, commit_id=commit_id)
    iac_repo = create_implementation_at_commit_repo(db_session)

    row = iac_repo.upsert_evaluation(
        spec_item_id=item_id,
        commit_id=commit_id,
        implemented=True,
        summary="Implemented in src/main.py",
        gaps=[],
        confidence=0.9,
    )

    assert row.implemented is True
    assert row.summary == "Implemented in src/main.py"
    assert row.gaps == []
    assert row.confidence == 0.9

    updated = iac_repo.upsert_evaluation(
        spec_item_id=item_id,
        commit_id=commit_id,
        implemented=False,
        summary="Not yet",
        gaps=["missing handler"],
        confidence=0.2,
    )
    assert updated.id == row.id
    assert updated.implemented is False
    assert updated.summary == "Not yet"
    assert updated.gaps == ["missing handler"]
    assert updated.confidence == 0.2


def test_get_for_spec_item_at_commit(
    db_session: Session,
    git_repo_id: int,
    commit_id: int,
) -> None:
    item_id = _make_spec_item(db_session, git_repo_id=git_repo_id, commit_id=commit_id)
    iac_repo = create_implementation_at_commit_repo(db_session)
    created = iac_repo.upsert_evaluation(
        spec_item_id=item_id,
        commit_id=commit_id,
        implemented=True,
        summary="ok",
        gaps=[],
        confidence=0.5,
    )

    found = iac_repo.get_for_spec_item_at_commit(spec_item_id=item_id, commit_id=commit_id)
    assert found is not None
    assert found.id == created.id
