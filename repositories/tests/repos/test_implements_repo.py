"""Tests for `ImplementsRepo`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_implements_repo,
    create_requirement_repo,
    create_requirement_version_repo,
    create_spec_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus


def test_add_and_get_round_trip(db_session: Session, git_repo_id: int) -> None:
    ts = datetime.now(UTC)
    spec = create_spec_repo(db_session).add(paper_id="0001-impl", repo_id=git_repo_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    rv = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_sha="a" * 40,
        commit_datetime=ts,
        requirement_text="t",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    art = create_artifact_repo(db_session).add(filepath="a.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_sha="b" * 40,
        commit_datetime=ts,
        status="active",
        file_content="c",
    )

    repo = create_implements_repo(db_session)
    row = repo.add(requirement_version_id=rv.id, artifact_version_id=av.id)

    loaded = repo.get(requirement_version_id=rv.id, artifact_version_id=av.id)
    assert loaded is not None
    assert loaded.requirement_version_id == rv.id
    assert loaded.artifact_version_id == av.id
    assert row.requirement_version_id == rv.id

    by_pair = repo.get_by_requirement_version_and_artifact_version(
        requirement_version_id=rv.id,
        artifact_version_id=av.id,
    )
    assert by_pair is not None
    assert by_pair.requirement_version_id == rv.id
    assert by_pair.artifact_version_id == av.id


def test_update_evidence_for_filepath(db_session: Session, git_repo_id: int) -> None:
    ts = datetime.now(UTC)
    spec = create_spec_repo(db_session).add(paper_id="0001-evidence", repo_id=git_repo_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    rv = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_sha="a" * 40,
        commit_datetime=ts,
        requirement_text="t",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    art = create_artifact_repo(db_session).add(filepath="src/main.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_sha="b" * 40,
        commit_datetime=ts,
        status="active",
        file_content="def hello(): pass",
    )

    repo = create_implements_repo(db_session)
    repo.add(requirement_version_id=rv.id, artifact_version_id=av.id)

    updated = repo.update_evidence_for_filepath(
        requirement_version_id=rv.id,
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


def test_upsert_evidence_creates_row_when_missing(db_session: Session, git_repo_id: int) -> None:
    ts = datetime.now(UTC)
    spec = create_spec_repo(db_session).add(paper_id="0001-upsert", repo_id=git_repo_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    rv = create_requirement_version_repo(db_session).add(
        requirement_id=req.id,
        commit_sha="a" * 40,
        commit_datetime=ts,
        requirement_text="t",
        filepath_globs=[],
        status=VersionStatus.ACTIVE.value,
    )
    art = create_artifact_repo(db_session).add(filepath="src/main.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_sha="b" * 40,
        commit_datetime=ts,
        status="active",
        file_content="def hello(): pass",
    )

    repo = create_implements_repo(db_session)
    row = repo.upsert_evidence(
        requirement_version_id=rv.id,
        artifact_version_id=av.id,
        evidence_file="src/main.py",
        evidence_line_number=1,
        evidence_snippet="def hello(): pass",
        evidence_relevance="Defines hello behaviour.",
    )

    assert row.requirement_version_id == rv.id
    assert row.artifact_version_id == av.id
    assert row.evidence_snippet == "def hello(): pass"


def test_get_returns_none_when_pair_missing(db_session: Session) -> None:
    repo = create_implements_repo(db_session)
    assert repo.get(requirement_version_id=1, artifact_version_id=2) is None
