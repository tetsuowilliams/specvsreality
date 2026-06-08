"""Integration test for spec / spec-item / artifact schema via repos."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.repos import (
    create_artifact_candidate_repo,
    create_artifact_repo,
    create_artifact_version_repo,
    create_commit_repo,
    create_git_repo_repo,
    create_implementation_at_commit_repo,
    create_implements_repo,
    create_spec_item_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus

_DT = datetime(2026, 1, 15, tzinfo=UTC)


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return create_git_repo_repo(db_session).add(
        name="g",
        url="https://example.test/g.git",
        cursor_position="b" * 40,
        location="/tmp/g",
    ).id


def test_spec_graph_round_trip(db_session: Session, git_row_id: int) -> None:
    commit = create_commit_repo(db_session).get_or_create(
        repo_id=git_row_id,
        commit_sha="c" * 40,
        commit_message="add",
        committed_at=_DT,
    )
    spec = create_spec_repo(db_session).add(paper_id="0001-spec-graph", repo_id=git_row_id)
    version = create_spec_version_repo(db_session).add(
        spec_id=spec.id,
        commit_id=commit.id,
        title="T",
        summary="S",
        spec_md="# s",
        tasks_md="- t",
        plan_md="p",
        created_at=_DT,
        status=VersionStatus.ACTIVE,
    )
    item = create_spec_item_repo(db_session).add(
        spec_version_id=version.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="do thing",
        source_quote="thing",
        importance=SpecItemImportance.MUST,
        success_criteria=["works"],
        failure_criteria=["broken"],
    )
    art = create_artifact_repo(db_session).add(filepath="src/f.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id=commit.id,
        status="active",
        file_content="x = 1",
    )
    candidate = create_artifact_candidate_repo(db_session).add(
        spec_version_id=version.id,
        artifact_version_id=av.id,
        reasoning="looks relevant",
    )
    iac = create_implementation_at_commit_repo(db_session).upsert_evaluation(
        spec_item_id=item.id,
        commit_id=commit.id,
        implemented=True,
        summary="ok",
        gaps=[],
        confidence=0.9,
    )
    impl = create_implements_repo(db_session).add(
        implementation_at_commit_id=iac.id,
        artifact_version_id=av.id,
    )

    assert impl.implementation_at_commit_id == iac.id
    assert impl.artifact_version_id == av.id
    assert candidate.spec_version_id == version.id

    # Force a reload from the database to exercise the PG enum result processor.
    db_session.expire_all()
    reloaded = create_spec_item_repo(db_session).list_for_spec_version(spec_version_id=version.id)
    assert len(reloaded) == 1
    assert reloaded[0].item_type is SpecItemType.FUNCTIONAL_BEHAVIOR
    assert reloaded[0].importance is SpecItemImportance.MUST
    assert reloaded[0].item_type.value == "functional_behavior"


def test_artifact_version_repo_get_latest_for_artifact_filepath(
    db_session: Session, git_row_id: int
) -> None:
    commit_repo = create_commit_repo(db_session)
    c_old = commit_repo.get_or_create(
        repo_id=git_row_id, commit_sha="a" * 40, commit_message="old", committed_at=_DT
    )
    c_new = commit_repo.get_or_create(
        repo_id=git_row_id,
        commit_sha="b" * 40,
        commit_message="new",
        committed_at=_DT + timedelta(seconds=30),
    )
    artifact_repo = create_artifact_repo(db_session)
    artifact_version_repo = create_artifact_version_repo(db_session)

    path = "src/lib.py"
    art = artifact_repo.add(filepath=path)
    artifact_version_repo.add(artifact_id=art.id, commit_id=c_old.id, status="active", file_content="v1")
    av_new = artifact_version_repo.add(
        artifact_id=art.id, commit_id=c_new.id, status="active", file_content="v2"
    )

    latest = artifact_version_repo.get_latest_for_artifact_filepath(filepath=path)
    assert latest is not None
    assert latest.id == av_new.id
    assert latest.file_content == "v2"

    assert artifact_version_repo.get_latest_for_artifact_filepath(filepath="missing/nope.py") is None
