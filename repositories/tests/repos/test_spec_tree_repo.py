"""Tests for `SpecTreeRepo`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_implementation_at_commit_repo,
    create_implements_repo,
    create_spec_tree_repo,
)
from tests.fixtures.graph import add_commit, add_spec, add_spec_item, add_spec_version

_DT = datetime(2026, 1, 15, tzinfo=UTC)


def _build_tree(db_session: Session, *, git_repo_id: int) -> dict[str, int]:
    earlier = add_commit(
        db_session,
        repo_id=git_repo_id,
        commit_sha="a" * 40,
        committed_at=_DT,
    )
    later = add_commit(
        db_session,
        repo_id=git_repo_id,
        commit_sha="b" * 40,
        committed_at=_DT + timedelta(days=1),
    )
    spec = add_spec(db_session, paper_id="specs/tree", repo_id=git_repo_id)
    v1 = add_spec_version(db_session, spec_id=spec.id, commit_id=earlier.id, spec_md="# v1")
    v2 = add_spec_version(db_session, spec_id=spec.id, commit_id=later.id, spec_md="# v2")
    item = add_spec_item(db_session, spec_version_id=v2.id, local_key="FR-1")
    art = create_artifact_repo(db_session).add(filepath="src/main.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id=later.id,
        status="active",
        file_content="code",
    )
    iac = create_implementation_at_commit_repo(db_session).upsert_evaluation(
        spec_item_id=item.id,
        commit_id=later.id,
        implemented=True,
        summary="ok",
        gaps=[],
        confidence=0.9,
    )
    create_implements_repo(db_session).add(
        implementation_at_commit_id=iac.id,
        artifact_version_id=av.id,
    )
    return {
        "spec_id": spec.id,
        "earlier_commit_id": earlier.id,
        "later_commit_id": later.id,
        "v1_id": v1.id,
        "v2_id": v2.id,
        "item_id": item.id,
        "iac_id": iac.id,
    }


def test_list_versions_with_commit_orders_by_committed_at(
    db_session: Session, git_repo_id: int
) -> None:
    ids = _build_tree(db_session, git_repo_id=git_repo_id)
    repo = create_spec_tree_repo(db_session)

    rows = repo.list_versions_with_commit(spec_id=ids["spec_id"])
    assert len(rows) == 2
    assert rows[0][0].id == ids["v1_id"]
    assert rows[1][0].id == ids["v2_id"]
    assert rows[0][1].id == ids["earlier_commit_id"]
    assert rows[1][1].id == ids["later_commit_id"]


def test_get_latest_version_with_commit(db_session: Session, git_repo_id: int) -> None:
    ids = _build_tree(db_session, git_repo_id=git_repo_id)
    repo = create_spec_tree_repo(db_session)

    latest = repo.get_latest_version_with_commit(spec_id=ids["spec_id"])
    assert latest is not None
    version, commit = latest
    assert version.id == ids["v2_id"]
    assert commit.id == ids["later_commit_id"]


def test_get_version_with_commit_at_commit(db_session: Session, git_repo_id: int) -> None:
    ids = _build_tree(db_session, git_repo_id=git_repo_id)
    repo = create_spec_tree_repo(db_session)

    at_earlier = repo.get_version_with_commit_at_commit(
        spec_id=ids["spec_id"],
        commit_id=ids["earlier_commit_id"],
    )
    assert at_earlier is not None
    assert at_earlier[0].id == ids["v1_id"]

    missing = repo.get_version_with_commit_at_commit(
        spec_id=ids["spec_id"],
        commit_id=999_999_999,
    )
    assert missing is None


def test_get_latest_version_with_commit_at_or_before_commit(
    db_session: Session, git_repo_id: int
) -> None:
    ids = _build_tree(db_session, git_repo_id=git_repo_id)
    repo = create_spec_tree_repo(db_session)

    at_earlier = repo.get_latest_version_with_commit_at_or_before_commit(
        spec_id=ids["spec_id"],
        commit_id=ids["earlier_commit_id"],
    )
    assert at_earlier is not None
    assert at_earlier[0].id == ids["v1_id"]

    at_later = repo.get_latest_version_with_commit_at_or_before_commit(
        spec_id=ids["spec_id"],
        commit_id=ids["later_commit_id"],
    )
    assert at_later is not None
    assert at_later[0].id == ids["v2_id"]


def test_list_items_for_versions(db_session: Session, git_repo_id: int) -> None:
    ids = _build_tree(db_session, git_repo_id=git_repo_id)
    repo = create_spec_tree_repo(db_session)

    assert repo.list_items_for_versions(spec_version_ids=[]) == []

    items = repo.list_items_for_versions(spec_version_ids=[ids["v2_id"]])
    assert len(items) == 1
    assert items[0].id == ids["item_id"]


def test_list_implementations_with_commit(db_session: Session, git_repo_id: int) -> None:
    ids = _build_tree(db_session, git_repo_id=git_repo_id)
    repo = create_spec_tree_repo(db_session)

    assert repo.list_implementations_with_commit(spec_item_ids=[]) == []

    all_rows = repo.list_implementations_with_commit(spec_item_ids=[ids["item_id"]])
    assert len(all_rows) == 1
    assert all_rows[0][0].id == ids["iac_id"]

    filtered = repo.list_implementations_with_commit(
        spec_item_ids=[ids["item_id"]],
        commit_id=ids["later_commit_id"],
    )
    assert len(filtered) == 1


def test_list_implements_with_artifacts(db_session: Session, git_repo_id: int) -> None:
    ids = _build_tree(db_session, git_repo_id=git_repo_id)
    repo = create_spec_tree_repo(db_session)

    assert repo.list_implements_with_artifacts(implementation_at_commit_ids=[]) == []

    rows = repo.list_implements_with_artifacts(implementation_at_commit_ids=[ids["iac_id"]])
    assert len(rows) == 1
    impl, av, artifact = rows[0]
    assert impl.implementation_at_commit_id == ids["iac_id"]
    assert artifact.filepath == "src/main.py"


def test_get_latest_version_with_commit_returns_none_for_unknown_spec(
    db_session: Session,
) -> None:
    repo = create_spec_tree_repo(db_session)
    assert repo.get_latest_version_with_commit(spec_id=999_999_999) is None
