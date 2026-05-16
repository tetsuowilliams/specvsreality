"""Unit tests for `ArtifactMerge` (deps mocked)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from specvsreality_repositories.repos.enums import VersionStatus
from specvsreality_worker.agents.implements_agent.models import ImplementsAssessment
from specvsreality_worker.core import ArtifactMerge, CommitContext


@pytest.fixture
def commit() -> CommitContext:
    return CommitContext(
        repo_id=1,
        commit_sha="deadbeef",
        commit_datetime=datetime(2026, 2, 1, tzinfo=UTC),
    )


@pytest.fixture
def artifact_merge() -> ArtifactMerge:
    return ArtifactMerge(
        tree_scan=MagicMock(),
        git_adapter=MagicMock(),
        artifact_repo=MagicMock(),
        artifact_version_repo=MagicMock(),
        requirement_repo=MagicMock(),
        requirement_version_repo=MagicMock(),
        implements_repo=MagicMock(),
        implements_evaluation_agent=MagicMock(),
    )


def _assessment(*, implements: bool) -> ImplementsAssessment:
    return ImplementsAssessment(
        implements=implements,
        confidence="high" if implements else "low",
        reasoning="test",
        gaps=[] if implements else ["gap"],
    )


def test_merge_new_updated_returns_pair_when_glob_matches(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    rv = SimpleNamespace(id=7, filepath_globs=["src/**/*.py"])
    artifact_merge._requirement_version_repo.list_latest.return_value = [rv]
    artifact_merge._tree_scan.is_glob_match.return_value = True

    pairs = artifact_merge.merge_new_updated_artifact(relpath="src/mod.py", commit=commit)

    assert pairs == [(7, "src/mod.py")]
    artifact_merge._tree_scan.is_glob_match.assert_called()


def test_merge_new_updated_returns_empty_when_no_glob_matches(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    rv = SimpleNamespace(id=7, filepath_globs=["other/**"])
    artifact_merge._requirement_version_repo.list_latest.return_value = [rv]
    artifact_merge._tree_scan.is_glob_match.return_value = False

    pairs = artifact_merge.merge_new_updated_artifact(relpath="src/mod.py", commit=commit)

    assert pairs == []


def test_merge_new_updated_returns_multiple_rvs_when_each_matches_same_relpath(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    rv1 = SimpleNamespace(id=10, filepath_globs=["src/*.py"])
    rv2 = SimpleNamespace(id=20, filepath_globs=["*.py"])
    artifact_merge._requirement_version_repo.list_latest.return_value = [rv1, rv2]
    artifact_merge._tree_scan.is_glob_match.return_value = True
    relpath = "src/x.py"

    pairs = artifact_merge.merge_new_updated_artifact(relpath=relpath, commit=commit)

    assert set(pairs) == {(10, relpath), (20, relpath)}


def test_merge_deleted_does_not_add_version_without_prior_artifact_version(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    artifact_merge._artifact_version_repo.get_latest_for_artifact_filepath.return_value = None

    artifact_merge.merge_deleted_artifact(relpath="gone.py", commit=commit)

    artifact_merge._artifact_version_repo.add.assert_not_called()


def test_merge_deleted_adds_deleted_version_when_prior_version_exists(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    prior = SimpleNamespace(artifact_id=3)
    artifact_merge._artifact_version_repo.get_latest_for_artifact_filepath.return_value = prior

    artifact_merge.merge_deleted_artifact(relpath="tracked.py", commit=commit)

    artifact_merge._artifact_version_repo.add.assert_called_once()
    call = artifact_merge._artifact_version_repo.add.call_args
    assert call.kwargs["artifact_id"] == 3
    assert call.kwargs["status"] == VersionStatus.DELETED.value


def test_evaluate_creates_artifact_and_active_version_and_implements_when_new(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    rv = SimpleNamespace(requirement_text="Must do X")
    artifact_merge._requirement_version_repo.get_by_id.return_value = rv
    artifact_merge._git_adapter.file_at_commit.return_value = "code"
    artifact_merge._implements_evaluation_agent.evaluate.return_value = _assessment(implements=True)

    artifact_merge._artifact_repo.get_by_filepath.return_value = None
    new_artifact = SimpleNamespace(id=100)
    artifact_merge._artifact_repo.add.return_value = new_artifact
    artifact_merge._artifact_version_repo.get_latest_for_artifact_filepath.return_value = None
    artifact_merge._artifact_version_repo.get_by_filepath_and_commit.return_value = None
    new_av = SimpleNamespace(id=200)
    artifact_merge._artifact_version_repo.add.return_value = new_av

    artifact_merge.evaluate_and_merge_implementations(
        implementation_pairs=[(5, "lib/a.py")],
        commit=commit,
    )

    artifact_merge._artifact_repo.add.assert_called_once_with(filepath="lib/a.py")
    artifact_merge._artifact_version_repo.add.assert_called_once()
    av_call = artifact_merge._artifact_version_repo.add.call_args
    assert av_call.kwargs["artifact_id"] == 100
    assert av_call.kwargs["status"] == VersionStatus.ACTIVE.value
    assert av_call.kwargs["file_content"] == "code"

    artifact_merge._implements_repo.add.assert_called_once_with(
        requirement_version_id=5,
        artifact_version_id=200,
    )


def test_evaluate_uses_updated_status_and_links_new_version_when_prior_av_exists(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    rv = SimpleNamespace(requirement_text="req")
    artifact_merge._requirement_version_repo.get_by_id.return_value = rv
    artifact_merge._git_adapter.file_at_commit.return_value = "v2"
    artifact_merge._implements_evaluation_agent.evaluate.return_value = _assessment(implements=True)

    existing_art = SimpleNamespace(id=40)
    artifact_merge._artifact_repo.get_by_filepath.return_value = existing_art
    prior_av = SimpleNamespace(id=77)
    artifact_merge._artifact_version_repo.get_latest_for_artifact_filepath.return_value = prior_av
    artifact_merge._artifact_version_repo.get_by_filepath_and_commit.return_value = None
    new_av = SimpleNamespace(id=88)
    artifact_merge._artifact_version_repo.add.return_value = new_av

    artifact_merge.evaluate_and_merge_implementations(
        implementation_pairs=[(1, "lib/a.py")],
        commit=commit,
    )

    artifact_merge._artifact_repo.add.assert_not_called()
    artifact_merge._artifact_version_repo.add.assert_called_once()
    assert artifact_merge._artifact_version_repo.add.call_args.kwargs["status"] == VersionStatus.UPDATED.value
    artifact_merge._implements_repo.add.assert_called_once_with(
        requirement_version_id=1,
        artifact_version_id=88,
    )


def test_evaluate_does_nothing_when_not_implements_and_no_artifact_version(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    rv = SimpleNamespace(requirement_text="req")
    artifact_merge._requirement_version_repo.get_by_id.return_value = rv
    artifact_merge._git_adapter.file_at_commit.return_value = "x"
    artifact_merge._implements_evaluation_agent.evaluate.return_value = _assessment(implements=False)
    artifact_merge._artifact_version_repo.get_latest_for_artifact_filepath.return_value = None
    artifact_merge._artifact_version_repo.get_by_filepath_and_commit.return_value = None

    artifact_merge.evaluate_and_merge_implementations(
        implementation_pairs=[(9, "orphan.py")],
        commit=commit,
    )

    artifact_merge._artifact_version_repo.add.assert_not_called()
    artifact_merge._implements_repo.add.assert_not_called()


def test_evaluate_adds_updated_empty_version_when_not_implements_but_artifact_tracked(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    rv = SimpleNamespace(requirement_text="req")
    artifact_merge._requirement_version_repo.get_by_id.return_value = rv
    artifact_merge._git_adapter.file_at_commit.return_value = "x"
    artifact_merge._implements_evaluation_agent.evaluate.return_value = _assessment(implements=False)
    tracked = SimpleNamespace(artifact_id=50, id=999, commit_id=commit.commit_sha)
    artifact_merge._artifact_version_repo.get_latest_for_artifact_filepath.return_value = tracked
    artifact_merge._artifact_version_repo.get_by_filepath_and_commit.return_value = None
    artifact_merge._implements_repo.get_by_requirement_version_and_artifact_version.return_value = SimpleNamespace()
    artifact_merge._artifact_repo.get_by_filepath.return_value = SimpleNamespace(id=50)

    artifact_merge.evaluate_and_merge_implementations(
        implementation_pairs=[(9, "tracked.py")],
        commit=commit,
    )

    artifact_merge._artifact_version_repo.add.assert_called_once()
    call = artifact_merge._artifact_version_repo.add.call_args
    assert call.kwargs["artifact_id"] == 50
    assert call.kwargs["status"] == VersionStatus.UPDATED.value
    assert call.kwargs["file_content"] == ""
    artifact_merge._implements_repo.add.assert_not_called()


def test_evaluate_dedupes_artifact_version_per_path_per_commit_when_multiple_rvs_implement(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    """Regression: today we insert one AV per (rv, path) pair; we want one snapshot per (path, commit)."""
    rv = SimpleNamespace(requirement_text="req")
    artifact_merge._requirement_version_repo.get_by_id.return_value = rv
    artifact_merge._git_adapter.file_at_commit.return_value = "same snapshot"
    artifact_merge._implements_evaluation_agent.evaluate.return_value = _assessment(implements=True)

    existing_art = SimpleNamespace(id=40)
    artifact_merge._artifact_repo.get_by_filepath.return_value = existing_art
    artifact_merge._artifact_version_repo.get_latest_for_artifact_filepath.return_value = None
    first_av = SimpleNamespace(id=301)
    artifact_merge._artifact_version_repo.get_by_filepath_and_commit.side_effect = [None, first_av]
    artifact_merge._artifact_version_repo.add.return_value = first_av

    artifact_merge.evaluate_and_merge_implementations(
        implementation_pairs=[(1, "lib/a.py"), (2, "lib/a.py")],
        commit=commit,
    )

    artifact_merge._artifact_version_repo.add.assert_called_once()
    impl_calls = artifact_merge._implements_repo.add.call_args_list
    assert len(impl_calls) == 2
    assert impl_calls[0].kwargs["artifact_version_id"] == impl_calls[1].kwargs["artifact_version_id"]


def test_evaluate_dedupes_empty_marker_per_path_per_commit_when_multiple_rvs_reject_tracked_file(
    artifact_merge: ArtifactMerge,
    commit: CommitContext,
) -> None:
    """Else-branch: one empty UPDATED row per (path, commit) when multiple RVs reject."""
    rv = SimpleNamespace(requirement_text="req")
    artifact_merge._requirement_version_repo.get_by_id.return_value = rv
    artifact_merge._git_adapter.file_at_commit.return_value = "x"
    artifact_merge._implements_evaluation_agent.evaluate.return_value = _assessment(implements=False)
    tracked = SimpleNamespace(artifact_id=50, id=888, commit_id=commit.commit_sha)
    artifact_merge._artifact_version_repo.get_latest_for_artifact_filepath.return_value = tracked
    artifact_merge._artifact_version_repo.get_by_filepath_and_commit.side_effect = [
        None,
        SimpleNamespace(commit_id=commit.commit_sha),
    ]
    artifact_merge._implements_repo.get_by_requirement_version_and_artifact_version.return_value = SimpleNamespace()
    artifact_merge._artifact_repo.get_by_filepath.return_value = SimpleNamespace(id=50)

    artifact_merge.evaluate_and_merge_implementations(
        implementation_pairs=[(1, "lib/a.py"), (2, "lib/a.py")],
        commit=commit,
    )

    assert artifact_merge._artifact_version_repo.add.call_count == 1
    artifact_merge._implements_repo.add.assert_not_called()
