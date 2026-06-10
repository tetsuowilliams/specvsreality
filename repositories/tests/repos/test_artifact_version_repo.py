"""Tests for `ArtifactVersionRepo`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_artifact_repo,
    create_artifact_version_repo,
    create_commit_repo,
)
from tests.fixtures.graph import add_commit, add_git_repo

_DT = datetime(2026, 1, 15, tzinfo=UTC)


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return add_git_repo(
        db_session,
        name="av-repo",
        url="https://example.test/av.git",
        location="/tmp/av",
    ).id


def test_add_and_get_by_id(db_session: Session, commit_id: int) -> None:
    art = create_artifact_repo(db_session).add(filepath="f.py")
    repo = create_artifact_version_repo(db_session)
    row = repo.add(
        artifact_id=art.id,
        commit_id=commit_id,
        status="active",
        file_content="x",
    )

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.artifact_id == art.id
    assert loaded.commit_id == commit_id
    assert loaded.file_content == "x"


def test_get_by_id_returns_none_when_missing(db_session: Session) -> None:
    repo = create_artifact_version_repo(db_session)
    assert repo.get_by_id(999_999_999) is None


def test_get_by_filepath_and_commit_returns_matching_row(db_session: Session, git_row_id: int) -> None:
    cid = add_commit(db_session, repo_id=git_row_id, commit_sha="c" * 40).id
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
    cid = add_commit(db_session, repo_id=git_row_id, commit_sha="d" * 40).id
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
    cid = add_commit(db_session, repo_id=git_row_id, commit_sha="e" * 40).id
    other_cid = add_commit(db_session, repo_id=git_row_id, commit_sha="f" * 40).id
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
    cid = add_commit(db_session, repo_id=git_row_id, commit_sha="1" * 40).id
    art = create_artifact_repo(db_session).add(filepath="only/this.py")
    av_repo = create_artifact_version_repo(db_session)
    av_repo.add(
        artifact_id=art.id,
        commit_id=cid,
        status="active",
        file_content="",
    )

    assert av_repo.get_by_filepath_and_commit(filepath="other/path.py", commit_id=cid) is None


def test_get_latest_for_artifact_filepath(db_session: Session, git_row_id: int) -> None:
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
    artifact_version_repo.add(
        artifact_id=art.id, commit_id=c_old.id, status="active", file_content="v1"
    )
    av_new = artifact_version_repo.add(
        artifact_id=art.id, commit_id=c_new.id, status="active", file_content="v2"
    )

    latest = artifact_version_repo.get_latest_for_artifact_filepath(filepath=path)
    assert latest is not None
    assert latest.id == av_new.id
    assert latest.file_content == "v2"
    assert artifact_version_repo.get_latest_for_artifact_filepath(filepath="missing/nope.py") is None


def test_get_latest_for_artifact_filepath_at_or_before_commit(
    db_session: Session, git_row_id: int
) -> None:
    commit_repo = create_commit_repo(db_session)
    earlier = commit_repo.get_or_create(
        repo_id=git_row_id,
        commit_sha="a" * 40,
        commit_message="earlier",
        committed_at=datetime(2026, 1, 10, tzinfo=UTC),
    )
    later = commit_repo.get_or_create(
        repo_id=git_row_id,
        commit_sha="b" * 40,
        commit_message="later",
        committed_at=datetime(2026, 1, 20, tzinfo=UTC),
    )
    art = create_artifact_repo(db_session).add(filepath="src/app.py")
    av_repo = create_artifact_version_repo(db_session)
    first = av_repo.add(
        artifact_id=art.id,
        commit_id=earlier.id,
        status="active",
        file_content="v1",
    )
    av_repo.add(
        artifact_id=art.id,
        commit_id=later.id,
        status="updated",
        file_content="v2",
    )

    at_earlier = av_repo.get_latest_for_artifact_filepath_at_or_before_commit(
        filepath="src/app.py",
        commit_id=earlier.id,
    )
    assert at_earlier is not None
    assert at_earlier.id == first.id
    assert at_earlier.file_content == "v1"

    at_later = av_repo.get_latest_for_artifact_filepath_at_or_before_commit(
        filepath="src/app.py",
        commit_id=later.id,
    )
    assert at_later is not None
    assert at_later.file_content == "v2"


def test_get_by_filepath_and_commit_prefers_highest_id_on_duplicates(
    db_session: Session, git_row_id: int
) -> None:
    cid = add_commit(db_session, repo_id=git_row_id, commit_sha="9" * 40).id
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
