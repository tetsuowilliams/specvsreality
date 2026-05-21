"""Unit tests for `CommitWalker`."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from specvsreality_worker.core import CommitWalker
from specvsreality_worker.core.spec_detection import ArtifactType
from specvsreality_worker.git_adapter import ChangedPath, GitAdapter, GitCommitPathInformation, PathChangeState


def test_scan_commit_merges_specs_and_artifacts() -> None:
    adapter = MagicMock(spec=GitAdapter)
    changes = GitCommitPathInformation(
        paths=[
            ChangedPath(path="a.txt", state=PathChangeState.NEW, artifact_type=ArtifactType.CODE),
            ChangedPath(path="b.txt", state=PathChangeState.MODIFIED, artifact_type=ArtifactType.CODE),
        ]
    )
    adapter.changed_paths.return_value = changes
    commit_dt = datetime.now(UTC)
    adapter.commit_datetime.return_value = commit_dt

    spec_merge = MagicMock()
    artifact_merge = MagicMock()
    evaluation = MagicMock()

    CommitWalker(
        adapter,
        1,
        spec_merge,
        artifact_merge,
        evaluation,
    ).scan_commit("deadbeef")

    adapter.changed_paths.assert_called_once_with(commit_sha="deadbeef")
    adapter.commit_datetime.assert_called_once_with("deadbeef")

    commit = spec_merge.merge_specs.call_args.kwargs["commit"]
    assert commit.repo_id == 1
    assert commit.commit_sha == "deadbeef"
    assert commit.commit_datetime == commit_dt
    assert spec_merge.merge_specs.call_args.kwargs["changes"] == changes

    artifact_commit = artifact_merge.merge_artifacts.call_args.kwargs["commit"]
    assert artifact_commit.repo_id == 1
    assert artifact_commit.commit_sha == "deadbeef"
    assert artifact_merge.merge_artifacts.call_args.kwargs["changes"] == changes

    eval_commit = evaluation.evaluate_commit.call_args.kwargs["commit"]
    assert eval_commit.repo_id == 1
    assert eval_commit.commit_sha == "deadbeef"
    assert eval_commit.commit_datetime == commit_dt
