"""Unit tests for `SpecMerge`."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from specvsreality_worker.agents.spec_extraction_agent.models import SpecExtractionResult
from specvsreality_worker.core import CommitContext, SpecMerge
from specvsreality_worker.git_adapter import GitCommitPathInformation


class FakeGitAdapter:
    """
    Dict-backed git reads for orchestration tests.

    ``file_at_commit`` is required for ``spec.md``; ``file_at_commit_or_none`` is used
    for optional ``tasks.md`` / ``plan.md`` at the same commit path.
    """

    def __init__(self, contents: dict[str, str]) -> None:
        self._contents = {k.replace("\\", "/"): v for k, v in contents.items()}
        self.calls: list[tuple[str, str]] = []

    def file_at_commit(self, commit_sha: str, relpath: str) -> str:
        key = relpath.replace("\\", "/")
        self.calls.append((commit_sha, key))
        return self._contents[key]

    def file_at_commit_or_none(self, commit_sha: str, relpath: str) -> str | None:
        key = relpath.replace("\\", "/")
        self.calls.append((commit_sha, key))
        return self._contents.get(key)


def _make_spec_merge(fake_git: FakeGitAdapter) -> SpecMerge:
    return SpecMerge(
        spec_repo=MagicMock(),
        spec_version_repo=MagicMock(),
        requirement_version_repo=MagicMock(),
        requirement_merge=MagicMock(),
        artifact_merge=MagicMock(),
        spec_extraction_agent=MagicMock(),
        implements_evaluation_agent=MagicMock(),
        git_adapter=fake_git,
    )


@pytest.fixture
def spec_merge() -> SpecMerge:
    return _make_spec_merge(FakeGitAdapter({}))


@pytest.mark.parametrize("relpath", ["plan.md", "tasks.md", "spec.md"])
def test_is_spec_file_true_for_recognised_basenames_at_root(
    spec_merge: SpecMerge, relpath: str
) -> None:
    assert spec_merge._is_spec_file(relpath) is True


@pytest.mark.parametrize(
    "relpath",
    [
        "docs/plan.md",
        "specs/feature/spec.md",
        "a/b/c/tasks.md",
        "./plan.md",
        "docs\\plan.md",
    ],
)
def test_is_spec_file_true_for_recognised_basenames_in_subdirectories(
    spec_merge: SpecMerge, relpath: str
) -> None:
    assert spec_merge._is_spec_file(relpath) is True


@pytest.mark.parametrize("relpath", ["PLAN.md", "Tasks.MD", "Spec.Md", "docs/SPEC.md"])
def test_is_spec_file_is_case_insensitive(spec_merge: SpecMerge, relpath: str) -> None:
    assert spec_merge._is_spec_file(relpath) is True


@pytest.mark.parametrize(
    "relpath",
    [
        "",
        "README.md",
        "plan.txt",
        "plan",
        "specs/plan.md.bak",
        "tasks.md.tmp",
        "docs/plan.mdx",
    ],
)
def test_is_spec_file_false_for_non_spec_paths(spec_merge: SpecMerge, relpath: str) -> None:
    assert spec_merge._is_spec_file(relpath) is False


@pytest.mark.parametrize(
    ("relpath", "expected"),
    [
        ("specs/0001-spec-name-bla-bla/spec.md", "0001-spec-name-bla-bla"),
        ("specs/0042-foo/plan.md", "0042-foo"),
        ("specs/0042-foo/tasks.md", "0042-foo"),
        ("a/b/c/spec.md", "c"),
        ("specs\\0001-foo\\spec.md", "0001-foo"),
        ("./specs/0001-foo/spec.md", "0001-foo"),
    ],
)
def test_get_parent_spec_folder_returns_immediate_parent(
    spec_merge: SpecMerge, relpath: str, expected: str
) -> None:
    assert spec_merge._get_parent_spec_folder(relpath) == expected


@pytest.mark.parametrize("relpath", ["", "spec.md", "plan.md", "./spec.md"])
def test_get_parent_spec_folder_returns_none_when_no_parent_folder(
    spec_merge: SpecMerge, relpath: str
) -> None:
    assert spec_merge._get_parent_spec_folder(relpath) is None


def test_merge_specs_empty_changes_returns_empty_pairs_and_does_not_read_git() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = []
    changes = GitCommitPathInformation(new_files=[], modified_files=[], deleted_files=[])
    commit = CommitContext(
        repo_id=1,
        commit_sha="deadbeef",
        commit_datetime=datetime.now(UTC),
    )

    assert spec_merge.merge_specs(commit=commit, changes=changes) == []
    assert fake_git.calls == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()


def test_merge_specs_reads_tasks_and_plan_from_tree_when_only_spec_md_changed() -> None:
    """Sidecars are read from the commit tree even when this commit did not touch them."""
    fake_git = FakeGitAdapter(
        {
            "specs/0001-a/spec.md": "# Spec\n",
            "specs/0001-a/tasks.md": "- [ ] Task\n",
            "specs/0001-a/plan.md": "## Plan\n",
        }
    )
    spec_merge = _make_spec_merge(fake_git)
    extracted = SpecExtractionResult(spec_title="T", functional_requirements=[])
    spec_merge._spec_extraction_agent.extract_spec.return_value = extracted
    spec_merge._requirement_merge.merge_requirements.return_value = []
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = []

    db_spec = SimpleNamespace(id=501)
    spec_merge._spec_repo.get_by_paper_id.return_value = db_spec

    commit = CommitContext(
        repo_id=7,
        commit_sha="abc123",
        commit_datetime=datetime.now(UTC),
    )
    changes = GitCommitPathInformation(
        new_files=[],
        modified_files=["specs/0001-a/spec.md"],
        deleted_files=[],
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    assert fake_git.calls == [
        ("abc123", "specs/0001-a/spec.md"),
        ("abc123", "specs/0001-a/tasks.md"),
        ("abc123", "specs/0001-a/plan.md"),
    ]
    spec_merge._spec_extraction_agent.extract_spec.assert_called_once_with(
        spec_md="# Spec\n",
        tasks_md="- [ ] Task\n",
        plan_md="## Plan\n",
    )
    spec_merge._spec_version_repo.add.assert_called_once_with(
        spec_id=501,
        spec_md="# Spec\n",
        tasks_md="- [ ] Task\n",
        plan_md="## Plan\n",
    )


def test_merge_specs_reads_tasks_and_plan_from_tree_when_sidecars_missing() -> None:
    fake_git = FakeGitAdapter(
        {
            "specs/0001-a/spec.md": "S",
            "specs/0001-a/tasks.md": "T",
            "specs/0001-a/plan.md": "P",
        }
    )
    spec_merge = _make_spec_merge(fake_git)
    extracted = SpecExtractionResult(spec_title="T", functional_requirements=[])
    spec_merge._spec_extraction_agent.extract_spec.return_value = extracted
    spec_merge._requirement_merge.merge_requirements.return_value = []
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = []

    spec_merge._spec_repo.get_by_paper_id.return_value = SimpleNamespace(id=2)

    commit = CommitContext(
        repo_id=1,
        commit_sha="sha1",
        commit_datetime=datetime.now(UTC),
    )
    changes = GitCommitPathInformation(
        new_files=[],
        modified_files=[
            "specs/0001-a/spec.md",
            "specs/0001-a/tasks.md",
            "specs/0001-a/plan.md",
        ],
        deleted_files=[],
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    assert Counter(fake_git.calls) == Counter(
        [("sha1", "specs/0001-a/spec.md")] * 3
        + [("sha1", "specs/0001-a/tasks.md")] * 3
        + [("sha1", "specs/0001-a/plan.md")] * 3
    )
    # One pass per changed spec-kit path under the folder (same inputs each time).
    assert spec_merge._spec_extraction_agent.extract_spec.call_count == 3
    for call in spec_merge._spec_extraction_agent.extract_spec.call_args_list:
        assert call.kwargs == {"spec_md": "S", "tasks_md": "T", "plan_md": "P"}

    assert spec_merge._spec_version_repo.add.call_count == 3
    for call in spec_merge._spec_version_repo.add.call_args_list:
        assert call.kwargs == {"spec_id": 2, "spec_md": "S", "tasks_md": "T", "plan_md": "P"}


def test_merge_specs_loads_tasks_and_plan_from_same_spec_directory_as_changed_file() -> None:
    """Each live path uses spec/tasks/plan from its own parent folder at the commit (full tree read)."""
    fake_git = FakeGitAdapter(
        {
            "specs/feature-a/spec.md": "SA",
            "specs/feature-a/tasks.md": "TA",
            "specs/feature-a/plan.md": "PA",
            "specs/feature-b/spec.md": "SB",
            "specs/feature-b/tasks.md": "TB",
            "specs/feature-b/plan.md": "PB",
        }
    )
    spec_merge = _make_spec_merge(fake_git)
    extracted = SpecExtractionResult(spec_title="T", functional_requirements=[])
    spec_merge._spec_extraction_agent.extract_spec.return_value = extracted
    spec_merge._requirement_merge.merge_requirements.return_value = []
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = []

    spec_a = SimpleNamespace(id=10)
    spec_b = SimpleNamespace(id=20)

    def get_by_paper_id(*, paper_id: str, repo_id: int) -> SimpleNamespace:
        assert repo_id == 99
        return {"feature-a": spec_a, "feature-b": spec_b}[paper_id]

    spec_merge._spec_repo.get_by_paper_id.side_effect = get_by_paper_id

    commit = CommitContext(
        repo_id=99,
        commit_sha="sha9",
        commit_datetime=datetime.now(UTC),
    )
    changes = GitCommitPathInformation(
        new_files=[],
        modified_files=[
            "specs/feature-a/tasks.md",
            "specs/feature-b/plan.md",
        ],
        deleted_files=[],
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    assert fake_git.calls == [
        ("sha9", "specs/feature-a/spec.md"),
        ("sha9", "specs/feature-a/tasks.md"),
        ("sha9", "specs/feature-a/plan.md"),
        ("sha9", "specs/feature-b/spec.md"),
        ("sha9", "specs/feature-b/tasks.md"),
        ("sha9", "specs/feature-b/plan.md"),
    ]

    assert spec_merge._spec_extraction_agent.extract_spec.call_count == 2
    a_call, b_call = spec_merge._spec_extraction_agent.extract_spec.call_args_list
    assert a_call.kwargs == {"spec_md": "SA", "tasks_md": "TA", "plan_md": "PA"}
    assert b_call.kwargs == {"spec_md": "SB", "tasks_md": "TB", "plan_md": "PB"}

    assert spec_merge._spec_version_repo.add.call_count == 2
    va, vb = spec_merge._spec_version_repo.add.call_args_list
    assert va.kwargs == {"spec_id": 10, "spec_md": "SA", "tasks_md": "TA", "plan_md": "PA"}
    assert vb.kwargs == {"spec_id": 20, "spec_md": "SB", "tasks_md": "TB", "plan_md": "PB"}


def test_merge_specs_dedupes_implementation_pairs_before_evaluate() -> None:
    fake_git = FakeGitAdapter({"specs/x/spec.md": "body"})
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._spec_extraction_agent.extract_spec.return_value = SpecExtractionResult(
        spec_title="T",
        functional_requirements=[],
    )
    spec_merge._spec_repo.get_by_paper_id.return_value = SimpleNamespace(id=1)
    spec_merge._requirement_merge.merge_requirements.return_value = [(10, "src/a.py")]
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = [(10, "src/a.py")]

    commit = CommitContext(
        repo_id=1,
        commit_sha="s",
        commit_datetime=datetime.now(UTC),
    )
    changes = GitCommitPathInformation(
        new_files=["specs/x/spec.md"],
        modified_files=[],
        deleted_files=[],
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    spec_merge._artifact_merge.evaluate_and_merge_implementations.assert_called_once_with(
        implementation_pairs=[(10, "src/a.py")],
        commit=commit,
    )


def test_merge_specs_skips_extraction_when_spec_file_has_no_parent_folder() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = []

    commit = CommitContext(
        repo_id=1,
        commit_sha="s",
        commit_datetime=datetime.now(UTC),
    )
    changes = GitCommitPathInformation(
        new_files=["spec.md"],
        modified_files=[],
        deleted_files=[],
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    assert fake_git.calls == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()
    spec_merge._spec_version_repo.add.assert_not_called()
    spec_merge._artifact_merge.merge_new_updated_artifact.assert_called_once_with(
        relpath="spec.md",
        commit=commit,
    )


def test_merge_specs_non_spec_paths_do_not_trigger_git_reads() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = []

    commit = CommitContext(
        repo_id=1,
        commit_sha="s",
        commit_datetime=datetime.now(UTC),
    )
    changes = GitCommitPathInformation(
        new_files=["README.md", "src/main.py"],
        modified_files=[],
        deleted_files=[],
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    assert fake_git.calls == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()
    spec_merge._artifact_merge.merge_new_updated_artifact.assert_not_called()


def test_merge_specs_calls_merge_deleted_for_deleted_spec_files() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = []

    commit = CommitContext(
        repo_id=1,
        commit_sha="s",
        commit_datetime=datetime.now(UTC),
    )
    changes = GitCommitPathInformation(
        new_files=[],
        modified_files=[],
        deleted_files=["specs/old/spec.md"],
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    spec_merge._artifact_merge.merge_deleted_artifact.assert_called_once_with(
        relpath="specs/old/spec.md",
        commit=commit,
    )


def test_merge_specs_processes_each_spec_folder_once_per_live_spec_file() -> None:
    fake_git = FakeGitAdapter(
        {
            "specs/a/spec.md": "SA",
            "specs/b/spec.md": "SB",
            "specs/b/plan.md": "PB",
        }
    )
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._spec_extraction_agent.extract_spec.return_value = SpecExtractionResult(
        spec_title="T",
        functional_requirements=[],
    )
    spec_merge._requirement_merge.merge_requirements.return_value = []
    spec_merge._artifact_merge.merge_new_updated_artifact.return_value = []

    spec_a = SimpleNamespace(id=1)
    spec_b = SimpleNamespace(id=2)

    def get_by_paper_id(*, paper_id: str, repo_id: int) -> SimpleNamespace:
        assert repo_id == 3
        return {"a": spec_a, "b": spec_b}[paper_id]

    spec_merge._spec_repo.get_by_paper_id.side_effect = get_by_paper_id

    commit = CommitContext(
        repo_id=3,
        commit_sha="sha",
        commit_datetime=datetime.now(UTC),
    )
    changes = GitCommitPathInformation(
        new_files=[],
        modified_files=["specs/a/spec.md", "specs/b/plan.md"],
        deleted_files=[],
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    assert spec_merge._spec_extraction_agent.extract_spec.call_count == 2
    first, second = spec_merge._spec_extraction_agent.extract_spec.call_args_list
    assert first.kwargs == {"spec_md": "SA", "tasks_md": None, "plan_md": None}
    assert second.kwargs == {"spec_md": "SB", "tasks_md": None, "plan_md": "PB"}

    assert spec_merge._spec_version_repo.add.call_count == 2
    v1, v2 = spec_merge._spec_version_repo.add.call_args_list
    assert v1.kwargs == {"spec_id": 1, "spec_md": "SA", "tasks_md": None, "plan_md": None}
    assert v2.kwargs == {"spec_id": 2, "spec_md": "SB", "tasks_md": None, "plan_md": "PB"}

    paths = [c.kwargs["relpath"] for c in spec_merge._artifact_merge.merge_new_updated_artifact.call_args_list]
    assert paths == ["specs/a/spec.md", "specs/b/plan.md"]

