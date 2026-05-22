"""Tests for `ImplementationAtCommitRepo`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_implementation_at_commit_repo,
    create_requirement_repo,
    create_requirement_version_repo,
    create_spec_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus


def test_upsert_evaluation_persists_justification_fields(
    db_session: Session,
    git_repo_id: int,
) -> None:
    spec = create_spec_repo(db_session).add(paper_id="0001-eval", repo_id=git_repo_id)
    req = create_requirement_repo(db_session).add(spec_id=spec.id, paper_id="r")
    ts = datetime.now(UTC)
    rv_repo = create_requirement_version_repo(db_session)
    rv = rv_repo.add(
        requirement_id=req.id,
        commit_sha="a" * 40,
        commit_datetime=ts,
        requirement_text="text",
        filepath_globs=["*.py"],
        status=VersionStatus.ACTIVE.value,
    )

    iac_repo = create_implementation_at_commit_repo(db_session)
    row = iac_repo.upsert_evaluation(
        requirement_version_id=rv.id,
        evaluation_commit_sha="b" * 40,
        implemented=True,
        summary="Implemented in src/main.py",
        gaps=[],
        confidence="high",
    )

    assert row.implemented is True
    assert row.summary == "Implemented in src/main.py"
    assert row.gaps == []
    assert row.confidence == "high"

    updated = iac_repo.upsert_evaluation(
        requirement_version_id=rv.id,
        evaluation_commit_sha="b" * 40,
        implemented=False,
        summary="Not yet",
        gaps=["missing handler"],
        confidence="low",
    )
    assert updated.id == row.id
    assert updated.implemented is False
    assert updated.summary == "Not yet"
    assert updated.gaps == ["missing handler"]
