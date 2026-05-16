"""Tests for `ArtifactRepo`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_artifact_repo


def test_add_get_by_filepath_and_get_by_id(db_session: Session) -> None:
    repo = create_artifact_repo(db_session)
    row = repo.add(filepath="src/pkg/mod.py")

    assert repo.get_by_filepath("src/pkg/mod.py") == row
    assert repo.get_by_id(row.id) == row


def test_get_by_filepath_returns_none_when_missing(db_session: Session) -> None:
    repo = create_artifact_repo(db_session)
    assert repo.get_by_filepath("nope.py") is None


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_artifact_repo(db_session)
    assert repo.get_by_id(999_999_999) is None
