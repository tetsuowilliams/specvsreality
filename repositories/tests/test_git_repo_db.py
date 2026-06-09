"""Baseline git_repo table DB integration test."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def test_git_repo_round_trip(db_session: Session, git_repo_id) -> None:
    row = db_session.execute(
        text(
            "SELECT id, name, url, cursor_position, location, clone_error FROM git_repo WHERE id = :id",
        ),
        {"id": git_repo_id},
    ).one()
    assert row.name == "repo"
    assert row.url == "https://example.test/repo.git"
    assert row.cursor_position == "a" * 40
    assert row.location == "/tmp/repo"
    assert row.clone_error == ""
