"""Tests for ``ArtifactVersionRepo``."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_git_repo_repo,
)


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return create_git_repo_repo(db_session).add(
        name="av-repo",
        url="https://example.test/av.git",
        cursor_position="a" * 40,
        location="/tmp/av",
    ).id


def test_get_by_filepath_and_commit_returns_matching_row(db_session: Session, git_row_id: int) -> None:
    _ = git_row_id
    ts = datetime.now(UTC)
    commit = "c" * 40
    art = create_artifact_repo(db_session).add(filepath="src/module.py")
    av_repo = create_artifact_version_repo(db_session)
    expected = av_repo.add(
        artifact_id=art.id,
        commit_sha=commit,
        commit_datetime=ts,
        status="active",
        file_content="print(1)",
    )

    found = av_repo.get_by_filepath_and_commit(filepath="src/module.py", commit_sha=commit)

    assert found is not None
    assert found.id == expected.id
    assert found.file_content == "print(1)"


def test_get_by_filepath_and_commit_normalizes_backslashes(db_session: Session, git_row_id: int) -> None:
    _ = git_row_id
    ts = datetime.now(UTC)
    commit = "d" * 40
    art = create_artifact_repo(db_session).add(filepath="src/nested/file.py")
    av_repo = create_artifact_version_repo(db_session)
    expected = av_repo.add(
        artifact_id=art.id,
        commit_sha=commit,
        commit_datetime=ts,
        status="active",
        file_content="x",
    )

    found = av_repo.get_by_filepath_and_commit(filepath=r"src\nested\file.py", commit_sha=commit)

    assert found is not None
    assert found.id == expected.id


def test_get_by_filepath_and_commit_returns_none_wrong_commit(db_session: Session, git_row_id: int) -> None:
    _ = git_row_id
    ts = datetime.now(UTC)
    art = create_artifact_repo(db_session).add(filepath="lib/x.py")
    av_repo = create_artifact_version_repo(db_session)
    av_repo.add(
        artifact_id=art.id,
        commit_sha="e" * 40,
        commit_datetime=ts,
        status="active",
        file_content="a",
    )

    assert av_repo.get_by_filepath_and_commit(filepath="lib/x.py", commit_sha="f" * 40) is None


def test_get_by_filepath_and_commit_returns_none_unknown_path(db_session: Session, git_row_id: int) -> None:
    _ = git_row_id
    ts = datetime.now(UTC)
    commit = "1" * 40
    art = create_artifact_repo(db_session).add(filepath="only/this.py")
    av_repo = create_artifact_version_repo(db_session)
    av_repo.add(
        artifact_id=art.id,
        commit_sha=commit,
        commit_datetime=ts,
        status="active",
        file_content="",
    )

    assert av_repo.get_by_filepath_and_commit(filepath="other/path.py", commit_sha=commit) is None


def test_get_by_filepath_and_commit_prefers_highest_id_on_duplicates(db_session: Session, git_row_id: int) -> None:
    _ = git_row_id
    ts = datetime.now(UTC)
    commit = "9" * 40
    art = create_artifact_repo(db_session).add(filepath="dup/path.py")
    av_repo = create_artifact_version_repo(db_session)
    first = av_repo.add(
        artifact_id=art.id,
        commit_sha=commit,
        commit_datetime=ts,
        status="updated",
        file_content="first",
    )
    second = av_repo.add(
        artifact_id=art.id,
        commit_sha=commit,
        commit_datetime=ts,
        status="updated",
        file_content="second",
    )

    found = av_repo.get_by_filepath_and_commit(filepath="dup/path.py", commit_sha=commit)

    assert found is not None
    assert found.id == second.id
    assert found.id != first.id
    assert found.file_content == "second"
