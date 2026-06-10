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


def test_get_by_id(db_session: Session, git_repo_id: int, commit_id: int) -> None:
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

    loaded = iac_repo.get_by_id(created.id)
    assert loaded is not None
    assert loaded.id == created.id
    assert iac_repo.get_by_id(999_999_999) is None


def test_list_for_spec_items(db_session: Session, git_repo_id: int, commit_id: int) -> None:
    item_id = _make_spec_item(db_session, git_repo_id=git_repo_id, commit_id=commit_id)
    iac_repo = create_implementation_at_commit_repo(db_session)
    assert iac_repo.list_for_spec_items(spec_item_ids=[]) == []

    created = iac_repo.upsert_evaluation(
        spec_item_id=item_id,
        commit_id=commit_id,
        implemented=True,
        summary="ok",
        gaps=[],
        confidence=0.5,
    )
    rows = iac_repo.list_for_spec_items(spec_item_ids=[item_id])
    assert len(rows) == 1
    assert rows[0].id == created.id


def test_get_latest_for_spec_item(db_session: Session, git_repo_id: int) -> None:
    from datetime import UTC, datetime

    from specvsreality_repositories.repos import create_commit_repo

    commit_repo = create_commit_repo(db_session)
    earlier = commit_repo.get_or_create(
        repo_id=git_repo_id,
        commit_sha="a" * 40,
        commit_message="earlier",
        committed_at=datetime(2026, 1, 10, tzinfo=UTC),
    )
    later = commit_repo.get_or_create(
        repo_id=git_repo_id,
        commit_sha="b" * 40,
        commit_message="later",
        committed_at=datetime(2026, 1, 20, tzinfo=UTC),
    )
    item_id = _make_spec_item(db_session, git_repo_id=git_repo_id, commit_id=earlier.id)
    iac_repo = create_implementation_at_commit_repo(db_session)
    iac_repo.upsert_evaluation(
        spec_item_id=item_id,
        commit_id=earlier.id,
        implemented=False,
        summary="old",
        gaps=[],
        confidence=0.2,
    )
    latest = iac_repo.upsert_evaluation(
        spec_item_id=item_id,
        commit_id=later.id,
        implemented=True,
        summary="new",
        gaps=[],
        confidence=0.9,
    )

    found = iac_repo.get_latest_for_spec_item(spec_item_id=item_id)
    assert found is not None
    assert found.id == latest.id
    assert found.summary == "new"


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
