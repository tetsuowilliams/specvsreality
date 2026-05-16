"""Tests for `ArtifactVersionRepo`."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_artifact_repo, create_artifact_version_repo


def test_add_and_get_by_id(db_session: Session) -> None:
    art = create_artifact_repo(db_session).add(filepath="f.py")
    ts = datetime.now(UTC)
    repo = create_artifact_version_repo(db_session)
    row = repo.add(
        artifact_id=art.id,
        commit_id="a" * 40,
        commit_datetime=ts,
        status="active",
        file_content="x",
    )

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.artifact_id == art.id
    assert loaded.file_content == "x"


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_artifact_version_repo(db_session)
    assert repo.get_by_id(999_999_999) is None
