"""Tests for `ScanSelectionRepo`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_commit_repo,
    create_implementation_at_commit_repo,
    create_implements_repo,
    create_scan_selection_repo,
    create_spec_item_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus

_DT = datetime(2026, 1, 15, tzinfo=UTC)


def _add_commit(
    db_session: Session,
    *,
    git_repo_id: int,
    sha: str,
    committed_at: datetime,
) -> int:
    return create_commit_repo(db_session).get_or_create(
        repo_id=git_repo_id,
        commit_sha=sha,
        commit_message=f"commit {sha[:7]}",
        committed_at=committed_at,
    ).id


def _add_spec_with_items(
    db_session: Session,
    *,
    git_repo_id: int,
    commit_id: int,
    paper_id: str,
    implemented_flags: list[bool],
) -> tuple[int, list[int]]:
    spec = create_spec_repo(db_session).add(paper_id=paper_id, repo_id=git_repo_id)
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
    item_ids: list[int] = []
    for index, implemented in enumerate(implemented_flags, start=1):
        item = create_spec_item_repo(db_session).add(
            spec_version_id=version.id,
            local_key=f"FR-{index}",
            item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
            text="text",
            source_quote="q",
            importance=SpecItemImportance.MUST,
            success_criteria=[],
            failure_criteria=[],
        )
        item_ids.append(item.id)
        create_implementation_at_commit_repo(db_session).upsert_evaluation(
            spec_item_id=item.id,
            commit_id=commit_id,
            implemented=implemented,
            summary="s",
            gaps=[],
            confidence=0.9 if implemented else 0.2,
        )
    return spec.id, item_ids


def test_list_under_implemented_specs_at_commit(
    db_session: Session,
    git_repo_id: int,
) -> None:
    commit_id = _add_commit(
        db_session,
        git_repo_id=git_repo_id,
        sha="b" * 40,
        committed_at=_DT,
    )
    _add_spec_with_items(
        db_session,
        git_repo_id=git_repo_id,
        commit_id=commit_id,
        paper_id="specs/low",
        implemented_flags=[True, False, False],
    )
    _add_spec_with_items(
        db_session,
        git_repo_id=git_repo_id,
        commit_id=commit_id,
        paper_id="specs/high",
        implemented_flags=[True, True],
    )

    repo = create_scan_selection_repo(db_session)
    rows = repo.list_under_implemented_specs_at_commit(
        repo_id=git_repo_id,
        commit_id=commit_id,
        coverage_threshold=0.7,
    )

    assert [row.paper_id for row in rows] == ["specs/low"]
    assert rows[0].tracked == 3
    assert rows[0].implemented == 1


def test_list_specs_for_changed_artifacts_finds_historic_spec_via_prior_implements_link(
    db_session: Session,
    git_repo_id: int,
) -> None:
    earlier_id = _add_commit(
        db_session,
        git_repo_id=git_repo_id,
        sha="c" * 40,
        committed_at=_DT,
    )
    later_id = _add_commit(
        db_session,
        git_repo_id=git_repo_id,
        sha="d" * 40,
        committed_at=_DT + timedelta(days=1),
    )
    _, item_ids = _add_spec_with_items(
        db_session,
        git_repo_id=git_repo_id,
        commit_id=earlier_id,
        paper_id="specs/auth",
        implemented_flags=[True],
    )
    artifact = create_artifact_repo(db_session).add(filepath="src/auth.py")
    earlier_artifact_version = create_artifact_version_repo(db_session).add(
        artifact_id=artifact.id,
        commit_id=earlier_id,
        file_content="old code",
        status=VersionStatus.ACTIVE.value,
    )
    create_artifact_version_repo(db_session).add(
        artifact_id=artifact.id,
        commit_id=later_id,
        file_content="new code",
        status=VersionStatus.UPDATED.value,
    )
    iac = create_implementation_at_commit_repo(db_session).get_for_spec_item_at_commit(
        spec_item_id=item_ids[0],
        commit_id=earlier_id,
    )
    assert iac is not None
    create_implements_repo(db_session).upsert_evidence(
        implementation_at_commit_id=iac.id,
        artifact_version_id=earlier_artifact_version.id,
        evidence_file="src/auth.py",
        evidence_line_number=1,
        evidence_snippet="def auth",
        evidence_relevance="implements login",
    )

    repo = create_scan_selection_repo(db_session)
    rows = repo.list_specs_for_changed_artifacts_at_commit(commit_id=later_id)

    assert len(rows) == 1
    assert rows[0].paper_id == "specs/auth"
    assert rows[0].filepaths == ("src/auth.py",)
