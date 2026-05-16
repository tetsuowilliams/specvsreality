"""Tests for `GitRepoRepo`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import create_git_repo_repo


def test_add_round_trips_via_get_by_id(db_session: Session) -> None:
    repo = create_git_repo_repo(db_session)
    row = repo.add(
        name="my-repo",
        url="https://example.test/r.git",
        cursor_position="c" * 40,
        location="/data/r",
    )

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.name == "my-repo"
    assert loaded.url == "https://example.test/r.git"
    assert loaded.cursor_position == "c" * 40
    assert loaded.location == "/data/r"


def test_add_uses_default_cursor_and_location(db_session: Session) -> None:
    repo = create_git_repo_repo(db_session)
    row = repo.add(name="n", url="https://u")

    assert row.cursor_position == ""
    assert row.location == ""


def test_get_by_id_returns_none_for_unknown_id(db_session: Session) -> None:
    repo = create_git_repo_repo(db_session)
    assert repo.get_by_id(999_999_999) is None
