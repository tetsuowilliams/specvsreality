"""Tests for `ImplementsRepo`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_implementation_at_commit_repo,
    create_implements_repo,
    create_spec_item_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus

_DT = datetime(2026, 1, 15, tzinfo=UTC)


def _iac_id(db_session: Session, *, git_repo_id: int, commit_id: int) -> int:
    spec = create_spec_repo(db_session).add(paper_id=f"spec-{commit_id}", repo_id=git_repo_id)
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
        text="t",
        source_quote="q",
        importance=SpecItemImportance.MUST,
        success_criteria=[],
        failure_criteria=[],
    )
    row = create_implementation_at_commit_repo(db_session).upsert_evaluation(
        spec_item_id=item.id,
        commit_id=commit_id,
        implemented=True,
        summary="ok",
        gaps=[],
        confidence=0.8,
    )
    return row.id


def _artifact_version_id(db_session: Session, *, commit_id: int, filepath: str, content: str) -> int:
    art = create_artifact_repo(db_session).add(filepath=filepath)
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id=commit_id,
        status="active",
        file_content=content,
    )
    return av.id


def test_add_and_get_round_trip(db_session: Session, git_repo_id: int, commit_id: int) -> None:
    iac_id = _iac_id(db_session, git_repo_id=git_repo_id, commit_id=commit_id)
    av_id = _artifact_version_id(db_session, commit_id=commit_id, filepath="a.py", content="c")

    repo = create_implements_repo(db_session)
    row = repo.add(implementation_at_commit_id=iac_id, artifact_version_id=av_id)

    loaded = repo.get(implementation_at_commit_id=iac_id, artifact_version_id=av_id)
    assert loaded is not None
    assert loaded.implementation_at_commit_id == iac_id
    assert loaded.artifact_version_id == av_id
    assert row.implementation_at_commit_id == iac_id


def test_update_evidence_for_filepath(db_session: Session, git_repo_id: int, commit_id: int) -> None:
    iac_id = _iac_id(db_session, git_repo_id=git_repo_id, commit_id=commit_id)
    av_id = _artifact_version_id(
        db_session, commit_id=commit_id, filepath="src/main.py", content="def hello(): pass"
    )

    repo = create_implements_repo(db_session)
    repo.add(implementation_at_commit_id=iac_id, artifact_version_id=av_id)

    updated = repo.update_evidence_for_filepath(
        implementation_at_commit_id=iac_id,
        filepath="src/main.py",
        evidence_file="src/main.py",
        evidence_line_number=1,
        evidence_snippet="def hello(): pass",
        evidence_relevance="Defines hello behaviour.",
    )

    assert updated is not None
    assert updated.evidence_file == "src/main.py"
    assert updated.evidence_line_number == 1
    assert updated.evidence_snippet == "def hello(): pass"
    assert updated.evidence_relevance == "Defines hello behaviour."


def test_upsert_evidence_creates_row_when_missing(
    db_session: Session, git_repo_id: int, commit_id: int
) -> None:
    iac_id = _iac_id(db_session, git_repo_id=git_repo_id, commit_id=commit_id)
    av_id = _artifact_version_id(
        db_session, commit_id=commit_id, filepath="src/main.py", content="def hello(): pass"
    )

    repo = create_implements_repo(db_session)
    row = repo.upsert_evidence(
        implementation_at_commit_id=iac_id,
        artifact_version_id=av_id,
        evidence_file="src/main.py",
        evidence_line_number=1,
        evidence_snippet="def hello(): pass",
        evidence_relevance="Defines hello behaviour.",
    )

    assert row.implementation_at_commit_id == iac_id
    assert row.artifact_version_id == av_id
    assert row.evidence_snippet == "def hello(): pass"


def test_get_returns_none_when_pair_missing(db_session: Session) -> None:
    repo = create_implements_repo(db_session)
    assert repo.get(implementation_at_commit_id=1, artifact_version_id=2) is None
