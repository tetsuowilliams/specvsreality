"""Unit tests for `ArtifactMerge.merge_artifacts`."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from specvsreality_repositories.repos.enums import VersionStatus
from specvsreality_worker.core import ArtifactMerge, CommitContext
from specvsreality_worker.core.spec_detection import ArtifactType
from specvsreality_worker.git_adapter import ChangedPath, GitCommitPathInformation, PathChangeState


@pytest.fixture
def commit() -> CommitContext:
    return CommitContext(
        repo_id=1,
        commit_id=7,
        commit_sha="deadbeef",
        commit_datetime=datetime(2026, 2, 1, tzinfo=UTC),
        commit_message="msg",
    )


@pytest.fixture
def artifact_merge() -> ArtifactMerge:
    return ArtifactMerge(
        git_adapter=MagicMock(),
        artifact_repo=MagicMock(),
        artifact_version_repo=MagicMock(),
    )


def _code_change(path: str, state: PathChangeState) -> ChangedPath:
    return ChangedPath(path=path, state=state, artifact_type=ArtifactType.CODE)


def _spec_change(path: str, state: PathChangeState = PathChangeState.MODIFIED) -> ChangedPath:
    return ChangedPath(path=path, state=state, artifact_type=ArtifactType.SPEC)


def test_merge_artifacts_skips_spec_paths(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    artifact_merge.merge_artifacts(
        changes=GitCommitPathInformation(
            paths=[_spec_change("specs/x/spec.md", PathChangeState.NEW)]
        ),
        commit=commit,
    )

    artifact_merge._artifact_repo.add.assert_not_called()
    artifact_merge._artifact_version_repo.add.assert_not_called()


def test_merge_artifacts_creates_active_version_for_new_code_file(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    artifact_merge._artifact_repo.get_by_filepath.return_value = None
    artifact_merge._artifact_repo.add.return_value = SimpleNamespace(id=100)
    artifact_merge._git_adapter.file_at_commit.return_value = "print('hi')\n"

    artifact_merge.merge_artifacts(
        changes=GitCommitPathInformation(
            paths=[_code_change("src/main.py", PathChangeState.NEW)]
        ),
        commit=commit,
    )

    artifact_merge._artifact_repo.add.assert_called_once_with(filepath="src/main.py")
    artifact_merge._git_adapter.file_at_commit.assert_called_once_with(
        commit.commit_sha,
        "src/main.py",
    )
    artifact_merge._artifact_version_repo.add.assert_called_once_with(
        artifact_id=100,
        commit_id=commit.commit_id,
        status=VersionStatus.ACTIVE.value,
        file_content="print('hi')\n",
    )


def test_merge_artifacts_reuses_artifact_and_marks_modified_as_updated(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    existing = SimpleNamespace(id=40)
    artifact_merge._artifact_repo.get_by_filepath.return_value = existing
    artifact_merge._git_adapter.file_at_commit.return_value = "v2"

    artifact_merge.merge_artifacts(
        changes=GitCommitPathInformation(
            paths=[_code_change("lib/a.py", PathChangeState.MODIFIED)]
        ),
        commit=commit,
    )

    artifact_merge._artifact_repo.add.assert_not_called()
    artifact_merge._artifact_version_repo.add.assert_called_once_with(
        artifact_id=40,
        commit_id=commit.commit_id,
        status=VersionStatus.UPDATED.value,
        file_content="v2",
    )


def test_merge_artifacts_records_deleted_code_with_empty_content(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    existing = SimpleNamespace(id=50)
    artifact_merge._artifact_repo.get_by_filepath.return_value = existing

    artifact_merge.merge_artifacts(
        changes=GitCommitPathInformation(
            paths=[_code_change("gone.py", PathChangeState.DELETED)]
        ),
        commit=commit,
    )

    artifact_merge._git_adapter.file_at_commit.assert_not_called()
    artifact_merge._artifact_version_repo.add.assert_called_once_with(
        artifact_id=50,
        commit_id=commit.commit_id,
        status=VersionStatus.DELETED.value,
        file_content="",
    )


def test_merge_artifacts_records_every_changed_code_path(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    artifact_merge._artifact_repo.get_by_filepath.return_value = None
    artifact_merge._artifact_repo.add.side_effect = [
        SimpleNamespace(id=1),
        SimpleNamespace(id=2),
    ]
    artifact_merge._git_adapter.file_at_commit.side_effect = ["a", "b"]

    artifact_merge.merge_artifacts(
        changes=GitCommitPathInformation(
            paths=[
                _code_change("a.py", PathChangeState.NEW),
                _code_change("b.py", PathChangeState.NEW),
            ]
        ),
        commit=commit,
    )

    assert artifact_merge._artifact_version_repo.add.call_count == 2
