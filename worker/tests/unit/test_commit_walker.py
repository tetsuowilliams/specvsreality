"""Unit tests for `CommitWalker`."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from specvsreality_worker.core import CommitWalker, SpecMerge
from specvsreality_worker.git_adapter import GitAdapter, GitCommitPathInformation


def test_scan_commit_fetches_changed_paths_from_adapter() -> None:
    adapter = MagicMock(spec=GitAdapter)
    adapter.changed_paths.return_value = GitCommitPathInformation(
        new_files=["a.txt"],
        modified_files=["b.txt"],
        deleted_files=[],
    )
    adapter.commit_datetime.return_value = datetime.now(UTC)

    CommitWalker(
        adapter,
        1,
        SpecMerge(
            spec_repo=MagicMock(),
            spec_version_repo=MagicMock(),
            requirement_version_repo=MagicMock(),
            requirement_merge=MagicMock(),
            artifact_merge=MagicMock(),
            spec_extraction_agent=MagicMock(),
            implements_evaluation_agent=MagicMock(),
            git_adapter=adapter,
        ),
    ).scan_commit("deadbeef")

    adapter.changed_paths.assert_called_once_with("deadbeef")
