"""Unit tests for `CommitWalker`."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core import CommitWalker
from specvsreality_worker.core.spec_detection import ArtifactType
from specvsreality_worker.git_adapter import ChangedPath, GitAdapter, GitCommitPathInformation, PathChangeState


def test_scan_commit_runs_all_stages() -> None:
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
    adapter.commit_message.return_value = "the message"

    commit_repo = MagicMock()
    commit_repo.get_or_create.return_value = SimpleNamespace(
        id=42,
        committed_at=commit_dt,
        commit_message="the message",
    )

    artifact_merge = MagicMock()
    spec_merge = MagicMock()
    work = SimpleNamespace()
    spec_merge.merge_specs.return_value = [work]
    candidate_discovery = MagicMock()
    resolved = [SimpleNamespace()]
    candidate_discovery.discover.return_value = resolved
    implements_evaluation = MagicMock()
    settings = WorkerSettings()
    agent_run_metric_repo = MagicMock()

    CommitWalker(
        adapter,
        1,
        commit_repo,
        artifact_merge,
        spec_merge,
        candidate_discovery,
        implements_evaluation,
        settings=settings,
        agent_run_metric_repo=agent_run_metric_repo,
    ).scan_commit("deadbeef")

    adapter.changed_paths.assert_called_once_with(commit_sha="deadbeef")
    commit_repo.get_or_create.assert_called_once_with(
        repo_id=1,
        commit_sha="deadbeef",
        commit_message="the message",
        committed_at=commit_dt,
    )

    artifact_commit = artifact_merge.merge_artifacts.call_args.kwargs["commit"]
    assert artifact_commit.repo_id == 1
    assert artifact_commit.commit_id == 42
    assert artifact_commit.commit_sha == "deadbeef"
    assert artifact_merge.merge_artifacts.call_args.kwargs["changes"] == changes

    spec_commit = spec_merge.merge_specs.call_args.kwargs["commit"]
    assert spec_commit.commit_id == 42
    assert spec_merge.merge_specs.call_args.kwargs["changes"] == changes
    metrics = spec_merge.merge_specs.call_args.kwargs["metrics"]
    assert metrics is not None
    assert metrics.repo_id == 1
    assert metrics.commit_id == 42

    candidate_discovery.discover.assert_called_once_with(
        commit=spec_commit,
        work=work,
        metrics=metrics,
    )
    implements_evaluation.evaluate.assert_called_once_with(
        commit=spec_commit,
        work=work,
        candidates=resolved,
        metrics=metrics,
    )


def test_scan_commit_skips_downstream_when_no_specs_changed() -> None:
    adapter = MagicMock(spec=GitAdapter)
    adapter.changed_paths.return_value = GitCommitPathInformation(paths=[])
    adapter.commit_datetime.return_value = datetime.now(UTC)
    adapter.commit_message.return_value = "msg"

    commit_repo = MagicMock()
    commit_repo.get_or_create.return_value = SimpleNamespace(
        id=1,
        committed_at=datetime.now(UTC),
        commit_message="msg",
    )

    spec_merge = MagicMock()
    spec_merge.merge_specs.return_value = []
    candidate_discovery = MagicMock()
    implements_evaluation = MagicMock()

    CommitWalker(
        adapter,
        1,
        commit_repo,
        MagicMock(),
        spec_merge,
        candidate_discovery,
        implements_evaluation,
        settings=WorkerSettings(),
        agent_run_metric_repo=MagicMock(),
    ).scan_commit("deadbeef")

    candidate_discovery.discover.assert_not_called()
    implements_evaluation.evaluate.assert_not_called()
