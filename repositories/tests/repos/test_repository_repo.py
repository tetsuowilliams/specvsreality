"""Tests for ``RepositoryRepo``."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import RepositoryRepo


def test_add_round_trips_via_get_by_id(db_session: Session) -> None:
    repo = RepositoryRepo(db_session)
    row = repo.add(
        name="my-repo",
        url="https://example.test/r.git",
        clone_location="/data/r",
        cursor_position="c" * 40,
    )

    loaded = repo.get_by_id(row.id)
    assert loaded is not None
    assert loaded.name == "my-repo"
    assert loaded.url == "https://example.test/r.git"
    assert loaded.clone_location == "/data/r"
    assert loaded.cursor_position == "c" * 40
    assert loaded.default_branch == "main"


def test_get_or_create_is_idempotent_by_name(db_session: Session) -> None:
    repo = RepositoryRepo(db_session)
    first = repo.get_or_create(name="single", url="https://x")
    second = repo.get_or_create(name="single", url="https://x")
    assert first.id == second.id


def test_get_by_id_returns_none_for_unknown_id(db_session: Session) -> None:
    assert RepositoryRepo(db_session).get_by_id(999_999_999) is None


def test_list_all_orders_by_name(db_session: Session) -> None:
    repo = RepositoryRepo(db_session)
    repo.add(name="b", url="https://b")
    repo.add(name="a", url="https://a")
    rows = repo.list_all()
    assert [r.name for r in rows] == ["a", "b"]
