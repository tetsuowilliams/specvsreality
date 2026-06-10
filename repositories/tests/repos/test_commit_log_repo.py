"""Tests for `CommitLogRepo`."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import CommitLogAction
from specvsreality_repositories.repos import create_commit_log_repo


def test_append_and_list_for_commit(db_session: Session, commit_id: int) -> None:
    repo = create_commit_log_repo(db_session)
    repo.append(
        commit_id=commit_id,
        action=CommitLogAction.SPEC_EXTRACT.value,
        spec_folder="specs/auth",
        message="Launched spec extraction",
        reasoning="Spec folder touched in commit",
    )

    rows = repo.list_for_commit(commit_id=commit_id)
    assert len(rows) == 1
    assert rows[0].spec_folder == "specs/auth"
    assert rows[0].action == CommitLogAction.SPEC_EXTRACT.value


def test_list_sidebar_for_repo(db_session: Session, git_repo_id: int, commit_id: int) -> None:
    repo = create_commit_log_repo(db_session)
    repo.append(
        commit_id=commit_id,
        action=CommitLogAction.SPEC_RESCAN.value,
        spec_folder="specs/auth",
        message="Launched spec rescan",
        reasoning="Coverage below threshold",
    )

    sidebar = repo.list_sidebar_for_repo(repo_id=git_repo_id)
    assert len(sidebar) == 1
    assert sidebar[0].commit_id == commit_id
    assert sidebar[0].log_count == 1
