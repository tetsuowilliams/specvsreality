"""Unit tests for `sync_commit_artifacts`."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from specvsreality_worker.core.commit_sync import sync_commit_artifacts
from specvsreality_worker.core.spec_detection import ArtifactType
from specvsreality_worker.git_adapter import (
    ChangedPath,
    GitAdapter,
    GitCommitPathInformation,
    PathChangeState,
)


def test_sync_commit_artifacts_merges_code_changes() -> None:
    adapter = MagicMock(spec=GitAdapter)
    changes = GitCommitPathInformation(
        paths=[
            ChangedPath(path="a.txt", state=PathChangeState.NEW, artifact_type=ArtifactType.CODE),
        ]
    )
    adapter.changed_paths.return_value = changes
    commit_dt = datetime.now(UTC)
    adapter.commit_datetime.return_value = commit_dt
    adapter.commit_message.return_value = "the message"

    commit_repo = MagicMock()
    commit_repo.get_or_create.return_value = SimpleNamespace(
        id=42,
        committed_at=commit_dt,
        commit_message="the message",
    )
    artifact_merge = MagicMock()

    commit, returned_changes = sync_commit_artifacts(
        adapter,
        1,
        commit_repo,
        artifact_merge,
        "deadbeef",
    )

    adapter.changed_paths.assert_called_once_with(commit_sha="deadbeef")
    commit_repo.get_or_create.assert_called_once_with(
        repo_id=1,
        commit_sha="deadbeef",
        commit_message="the message",
        committed_at=commit_dt,
    )
    artifact_merge.merge_artifacts.assert_called_once()
    assert commit.repo_id == 1
    assert commit.commit_id == 42
    assert commit.commit_sha == "deadbeef"
    assert returned_changes == changes
