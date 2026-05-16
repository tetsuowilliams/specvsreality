"""Tests for catalog-related repo list methods."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_git_repo_repo,
    create_requirement_repo,
    create_spec_repo,
    create_spec_version_repo,
)


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return create_git_repo_repo(db_session).add(
        name="catalog",
        url="https://example.test/cat.git",
        cursor_position="a" * 40,
        location="/tmp/cat",
    ).id


def test_spec_list_for_repo_ordering(db_session: Session, git_row_id: int) -> None:
    spec_repo = create_spec_repo(db_session)
    s_b = spec_repo.add(paper_id="b-paper", repo_id=git_row_id)
    s_a = spec_repo.add(paper_id="a-paper", repo_id=git_row_id)
    rows = spec_repo.list_for_repo(repo_id=git_row_id)
    assert [r.id for r in rows] == [s_a.id, s_b.id]


def test_requirement_list_for_spec(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="p", repo_id=git_row_id)
    req_repo = create_requirement_repo(db_session)
    r1 = req_repo.add(spec_id=spec.id, paper_id="r1")
    r2 = req_repo.add(spec_id=spec.id, paper_id="r2")
    rows = req_repo.list_for_spec(spec_id=spec.id)
    assert [r.id for r in rows] == [r1.id, r2.id]


def test_spec_version_list_for_spec_ordered(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="p", repo_id=git_row_id)
    sv_repo = create_spec_version_repo(db_session)
    v1 = sv_repo.add(spec_id=spec.id, spec_md="s1", tasks_md="t1", plan_md="p1")
    v2 = sv_repo.add(spec_id=spec.id, spec_md="s2", tasks_md="t2", plan_md="p2")
    rows = sv_repo.list_for_spec_ordered(spec_id=spec.id)
    assert [r.id for r in rows] == [v1.id, v2.id]
    assert rows[0].spec_md == "s1"
