"""Tests for catalog-related repo list methods."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_commit_repo,
    create_git_repo_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_repositories.repos.enums import VersionStatus

_COMMIT_DT = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture()
def git_row_id(db_session: Session) -> int:
    return create_git_repo_repo(db_session).add(
        name="catalog",
        url="https://example.test/cat.git",
        cursor_position="a" * 40,
        location="/tmp/cat",
    ).id


def _commit(db_session: Session, repo_id: int, sha: str) -> int:
    return create_commit_repo(db_session).get_or_create(
        repo_id=repo_id,
        commit_sha=sha,
        commit_message="m",
        committed_at=_COMMIT_DT,
    ).id


def test_spec_list_for_repo_ordering(db_session: Session, git_row_id: int) -> None:
    spec_repo = create_spec_repo(db_session)
    s_b = spec_repo.add(paper_id="b-paper", repo_id=git_row_id)
    s_a = spec_repo.add(paper_id="a-paper", repo_id=git_row_id)
    rows = spec_repo.list_for_repo(repo_id=git_row_id)
    assert [r.id for r in rows] == [s_a.id, s_b.id]


def test_spec_version_list_for_spec_ordered(db_session: Session, git_row_id: int) -> None:
    spec = create_spec_repo(db_session).add(paper_id="p", repo_id=git_row_id)
    cid = _commit(db_session, git_row_id, "a" * 40)
    sv_repo = create_spec_version_repo(db_session)
    v1 = sv_repo.add(
        spec_id=spec.id,
        commit_id=cid,
        title="T1",
        summary="S1",
        spec_md="s1",
        tasks_md="t1",
        plan_md="p1",
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )
    v2 = sv_repo.add(
        spec_id=spec.id,
        commit_id=cid,
        title="T2",
        summary="S2",
        spec_md="s2",
        tasks_md="t2",
        plan_md="p2",
        created_at=_COMMIT_DT,
        status=VersionStatus.ACTIVE,
    )
    rows = sv_repo.list_for_spec_ordered(spec_id=spec.id)
    assert [r.id for r in rows] == [v1.id, v2.id]
    assert rows[0].spec_md == "s1"
