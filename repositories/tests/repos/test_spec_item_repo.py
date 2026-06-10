"""Tests for `SpecItemRepo`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.repos import create_spec_item_repo
from specvsreality_repositories.repos.enums import VersionStatus
from tests.fixtures.graph import add_spec, add_spec_item, add_spec_version


def test_add_and_get_by_id(db_session: Session, git_repo_id: int, commit_id: int) -> None:
    spec = add_spec(db_session, paper_id="0001-items", repo_id=git_repo_id)
    version = add_spec_version(db_session, spec_id=spec.id, commit_id=commit_id)
    repo = create_spec_item_repo(db_session)
    row = repo.add(
        spec_version_id=version.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="do thing",
        source_quote="thing",
        importance=SpecItemImportance.MUST,
        success_criteria=["works"],
        failure_criteria=["broken"],
    )

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.spec_version_id == version.id
    assert loaded.local_key == "FR-1"
    assert loaded.item_type is SpecItemType.FUNCTIONAL_BEHAVIOR
    assert loaded.importance is SpecItemImportance.MUST


def test_list_for_spec_version_returns_items_in_id_order(
    db_session: Session, git_repo_id: int, commit_id: int
) -> None:
    spec = add_spec(db_session, paper_id="0002-items", repo_id=git_repo_id)
    version = add_spec_version(db_session, spec_id=spec.id, commit_id=commit_id)
    repo = create_spec_item_repo(db_session)
    first = add_spec_item(db_session, spec_version_id=version.id, local_key="FR-1")
    second = add_spec_item(db_session, spec_version_id=version.id, local_key="FR-2")

    rows = repo.list_for_spec_version(spec_version_id=version.id)
    assert [r.id for r in rows] == [first.id, second.id]


def test_list_for_spec_version_persists_pg_enums_after_reload(
    db_session: Session, git_repo_id: int, commit_id: int
) -> None:
    spec = add_spec(db_session, paper_id="0003-enums", repo_id=git_repo_id)
    version = add_spec_version(
        db_session,
        spec_id=spec.id,
        commit_id=commit_id,
        status=VersionStatus.ACTIVE,
    )
    repo = create_spec_item_repo(db_session)
    repo.add(
        spec_version_id=version.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="do thing",
        source_quote="thing",
        importance=SpecItemImportance.MUST,
        success_criteria=["works"],
        failure_criteria=["broken"],
    )

    db_session.expire_all()
    reloaded = repo.list_for_spec_version(spec_version_id=version.id)
    assert len(reloaded) == 1
    assert reloaded[0].item_type is SpecItemType.FUNCTIONAL_BEHAVIOR
    assert reloaded[0].importance is SpecItemImportance.MUST
    assert reloaded[0].item_type.value == "functional_behavior"


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_spec_item_repo(db_session)
    assert repo.get_by_id(999_999_999) is None
