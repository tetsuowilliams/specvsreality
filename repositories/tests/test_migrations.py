"""Schema-level migration assertions."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine

EXPECTED_TABLES = {
    "alembic_version",
    "blobs",
    "commit_files",
    "commit_parents",
    "commits",
    "implementation_claims",
    "refs",
    "repositories",
    "requirement_versions",
    "requirements",
    "spec_versions",
    "specs",
}


def test_expected_tables_exist(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert tables == EXPECTED_TABLES


def test_current_claims_view_exists(engine: Engine) -> None:
    inspector = inspect(engine)
    assert "current_claims" in set(inspector.get_view_names())
