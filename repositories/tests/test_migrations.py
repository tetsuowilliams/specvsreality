"""Schema-level migration assertions."""

from __future__ import annotations

from sqlalchemy import inspect
from sqlalchemy.engine import Engine


def test_expected_tables_exist(engine: Engine) -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    expected = {
        "alembic_version",
        "agent_run_metric",
        "artifact",
        "artifact_candidate",
        "artifact_version",
        "commit",
        "git_repo",
        "implementation_at_commit",
        "implements",
        "spec",
        "spec_item",
        "spec_version",
    }
    assert expected.issubset(tables)
    assert tables - expected == set()
