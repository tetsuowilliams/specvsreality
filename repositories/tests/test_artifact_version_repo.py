"""Tests for ``ArtifactVersionRepo`` filepath/commit lookups."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_commit_repo,
    create_git_repo_repo,
)

_DT = datetime(2026, 1, 15, tzinfo=UTC)


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return create_git_repo_repo(db_session).add(
        name="av-repo",
        url="https://example.test/av.git",
        cursor_position="a" * 40,
        location="/tmp/av",
    ).id


def _commit(db_session: Session, repo_id: int, sha: str) -> int:
    return create_commit_repo(db_session).get_or_create(
        repo_id=repo_id,
        commit_sha=sha,
        commit_message="m",
        committed_at=_DT,
    ).id


def test_get_by_filepath_and_commit_returns_matching_row(db_session: Session, git_row_id: int) -> None:
    cid = _commit(db_session, git_row_id, "c" * 40)
    art = create_artifact_repo(db_session).add(filepath="src/module.py")
    av_repo = create_artifact_version_repo(db_session)
    expected = av_repo.add(
        artifact_id=art.id,
        commit_id=cid,
        status="active",
        file_content="print(1)",
    )

    found = av_repo.get_by_filepath_and_commit(filepath="src/module.py", commit_id=cid)

    assert found is not None
    assert found.id == expected.id
    assert found.file_content == "print(1)"


def test_get_by_filepath_and_commit_normalizes_backslashes(db_session: Session, git_row_id: int) -> None:
    cid = _commit(db_session, git_row_id, "d" * 40)
    art = create_artifact_repo(db_session).add(filepath="src/nested/file.py")
    av_repo = create_artifact_version_repo(db_session)
    expected = av_repo.add(
        artifact_id=art.id,
        commit_id=cid,
        status="active",
        file_content="x",
    )

    found = av_repo.get_by_filepath_and_commit(filepath=r"src\nested\file.py", commit_id=cid)

    assert found is not None
    assert found.id == expected.id


def test_get_by_filepath_and_commit_returns_none_wrong_commit(db_session: Session, git_row_id: int) -> None:
    cid = _commit(db_session, git_row_id, "e" * 40)
    other_cid = _commit(db_session, git_row_id, "f" * 40)
    art = create_artifact_repo(db_session).add(filepath="lib/x.py")
    av_repo = create_artifact_version_repo(db_session)
    av_repo.add(
        artifact_id=art.id,
        commit_id=cid,
        status="active",
        file_content="a",
    )

    assert av_repo.get_by_filepath_and_commit(filepath="lib/x.py", commit_id=other_cid) is None


def test_get_by_filepath_and_commit_returns_none_unknown_path(db_session: Session, git_row_id: int) -> None:
    cid = _commit(db_session, git_row_id, "1" * 40)
    art = create_artifact_repo(db_session).add(filepath="only/this.py")
    av_repo = create_artifact_version_repo(db_session)
    av_repo.add(
        artifact_id=art.id,
        commit_id=cid,
        status="active",
        file_content="",
    )

    assert av_repo.get_by_filepath_and_commit(filepath="other/path.py", commit_id=cid) is None


def test_get_by_filepath_and_commit_prefers_highest_id_on_duplicates(db_session: Session, git_row_id: int) -> None:
    cid = _commit(db_session, git_row_id, "9" * 40)
    art = create_artifact_repo(db_session).add(filepath="dup/path.py")
    av_repo = create_artifact_version_repo(db_session)
    first = av_repo.add(
        artifact_id=art.id,
        commit_id=cid,
        status="updated",
        file_content="first",
    )
    second = av_repo.add(
        artifact_id=art.id,
        commit_id=cid,
        status="updated",
        file_content="second",
    )

    found = av_repo.get_by_filepath_and_commit(filepath="dup/path.py", commit_id=cid)

    assert found is not None
    assert found.id == second.id
    assert found.id != first.id
    assert found.file_content == "second"
