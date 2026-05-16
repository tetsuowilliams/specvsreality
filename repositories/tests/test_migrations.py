"""Schema-level migration assertions."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def test_expected_tables_exist(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    expected = {
        "alembic_version",
        "artifact",
        "artifact_version",
        "git_repo",
        "implements",
        "requirement",
        "requirement_version",
        "spec",
        "spec_version",
    }
    assert expected.issubset(tables)
    assert tables - expected == set()
