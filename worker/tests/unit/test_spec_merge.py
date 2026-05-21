"""Unit tests for `SpecMerge`."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from specvsreality_repositories.repos.enums import VersionStatus
from specvsreality_worker.agents.spec_extraction_agent.models import SpecExtractionResult
from specvsreality_worker.core import CommitContext, SpecMerge
from specvsreality_worker.core.spec_detection import ArtifactType, SpecDetection
from specvsreality_worker.git_adapter import ChangedPath, GitCommitPathInformation, PathChangeState


class FakeGitAdapter:
    """Dict-backed git reads for orchestration tests."""

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


def _spec_change(path: str, state: PathChangeState = PathChangeState.MODIFIED) -> ChangedPath:
    return ChangedPath(path=path, state=state, artifact_type=ArtifactType.SPEC)


def _code_change(path: str, state: PathChangeState = PathChangeState.NEW) -> ChangedPath:
    return ChangedPath(path=path, state=state, artifact_type=ArtifactType.CODE)


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
        spec_detection=SpecDetection(),
    )


def _commit(*, repo_id: int = 1, sha: str = "abc123") -> CommitContext:
    return CommitContext(
        repo_id=repo_id,
        commit_sha=sha,
        commit_datetime=datetime(2026, 3, 1, tzinfo=UTC),
    )


def _expected_version_kwargs(commit: CommitContext) -> dict[str, object]:
    return {
        "commit_sha": commit.commit_sha,
        "created_at": commit.commit_datetime,
        "committed_at": commit.commit_datetime,
        "status": VersionStatus.ACTIVE.value,
    }


def test_merge_specs_empty_changes_does_not_read_git() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)
    commit = _commit()

    spec_merge.merge_specs(
        commit=commit,
        changes=GitCommitPathInformation(paths=[]),
    )

    assert fake_git.calls == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()
    spec_merge._spec_version_repo.add.assert_not_called()


def test_merge_specs_reads_tasks_and_plan_from_tree_when_only_spec_md_changed() -> None:
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
    spec_merge._spec_repo.get_by_paper_id.return_value = SimpleNamespace(id=501)
    commit = _commit(sha="abc123")

    spec_merge.merge_specs(
        commit=commit,
        changes=GitCommitPathInformation(paths=[_spec_change("specs/0001-a/spec.md")]),
    )

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
        **_expected_version_kwargs(commit),
    )
    spec_merge._requirement_merge.merge_requirements.assert_called_once_with(
        db_spec=spec_merge._spec_repo.get_by_paper_id.return_value,
        extracted_spec=extracted,
        commit=commit,
    )


def test_merge_specs_processes_each_changed_spec_file_separately() -> None:
    fake_git = FakeGitAdapter(
        {
            "specs/0001-a/spec.md": "S",
            "specs/0001-a/tasks.md": "T",
            "specs/0001-a/plan.md": "P",
        }
    )
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._spec_extraction_agent.extract_spec.return_value = SpecExtractionResult(
        spec_title="T",
        functional_requirements=[],
    )
    spec_merge._spec_repo.get_by_paper_id.return_value = SimpleNamespace(id=2)
    commit = _commit(sha="sha1")
    changes = GitCommitPathInformation(
        paths=[
            _spec_change("specs/0001-a/spec.md"),
            _spec_change("specs/0001-a/tasks.md"),
            _spec_change("specs/0001-a/plan.md"),
        ]
    )

    spec_merge.merge_specs(commit=commit, changes=changes)

    assert Counter(fake_git.calls) == Counter(
        [("sha1", "specs/0001-a/spec.md")] * 3
        + [("sha1", "specs/0001-a/tasks.md")] * 3
        + [("sha1", "specs/0001-a/plan.md")] * 3
    )
    assert spec_merge._spec_extraction_agent.extract_spec.call_count == 3
    assert spec_merge._spec_version_repo.add.call_count == 3
    for call in spec_merge._spec_version_repo.add.call_args_list:
        assert call.kwargs == {
            "spec_id": 2,
            "spec_md": "S",
            "tasks_md": "T",
            "plan_md": "P",
            **_expected_version_kwargs(commit),
        }


def test_merge_specs_loads_sidecars_from_each_spec_directory() -> None:
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
    spec_merge._spec_extraction_agent.extract_spec.return_value = SpecExtractionResult(
        spec_title="T",
        functional_requirements=[],
    )
    spec_a = SimpleNamespace(id=10)
    spec_b = SimpleNamespace(id=20)

    def get_by_paper_id(*, paper_id: str, repo_id: int) -> SimpleNamespace:
        assert repo_id == 99
        return {"feature-a": spec_a, "feature-b": spec_b}[paper_id]

    spec_merge._spec_repo.get_by_paper_id.side_effect = get_by_paper_id
    commit = _commit(repo_id=99, sha="sha9")

    spec_merge.merge_specs(
        commit=commit,
        changes=GitCommitPathInformation(
            paths=[
                _spec_change("specs/feature-a/tasks.md"),
                _spec_change("specs/feature-b/plan.md"),
            ]
        ),
    )

    assert fake_git.calls == [
        ("sha9", "specs/feature-a/spec.md"),
        ("sha9", "specs/feature-a/tasks.md"),
        ("sha9", "specs/feature-a/plan.md"),
        ("sha9", "specs/feature-b/spec.md"),
        ("sha9", "specs/feature-b/tasks.md"),
        ("sha9", "specs/feature-b/plan.md"),
    ]
    a_call, b_call = spec_merge._spec_extraction_agent.extract_spec.call_args_list
    assert a_call.kwargs == {"spec_md": "SA", "tasks_md": "TA", "plan_md": "PA"}
    assert b_call.kwargs == {"spec_md": "SB", "tasks_md": "TB", "plan_md": "PB"}


def test_merge_specs_creates_spec_when_missing() -> None:
    fake_git = FakeGitAdapter({"specs/x/spec.md": "body"})
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._spec_extraction_agent.extract_spec.return_value = SpecExtractionResult(
        spec_title="T",
        functional_requirements=[],
    )
    spec_merge._spec_repo.get_by_paper_id.return_value = None
    spec_merge._spec_repo.add.return_value = SimpleNamespace(id=77)
    commit = _commit()

    spec_merge.merge_specs(
        commit=commit,
        changes=GitCommitPathInformation(paths=[_spec_change("specs/x/spec.md", PathChangeState.NEW)]),
    )

    spec_merge._spec_repo.add.assert_called_once_with(paper_id="x", repo_id=1)
    spec_merge._spec_version_repo.add.assert_called_once_with(
        spec_id=77,
        spec_md="body",
        tasks_md=None,
        plan_md=None,
        **_expected_version_kwargs(commit),
    )


def test_merge_specs_skips_extraction_when_spec_file_has_no_parent_folder() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)
    commit = _commit()

    spec_merge.merge_specs(
        commit=commit,
        changes=GitCommitPathInformation(paths=[_spec_change("spec.md", PathChangeState.NEW)]),
    )

    assert fake_git.calls == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()
    spec_merge._spec_version_repo.add.assert_not_called()


def test_merge_specs_ignores_code_paths() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)
    commit = _commit()

    spec_merge.merge_specs(
        commit=commit,
        changes=GitCommitPathInformation(
            paths=[
                _code_change("README.md"),
                _code_change("src/main.py"),
            ]
        ),
    )

    assert fake_git.calls == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()


def test_merge_specs_still_extracts_when_sidecars_missing() -> None:
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
    spec_a = SimpleNamespace(id=1)
    spec_b = SimpleNamespace(id=2)

    def get_by_paper_id(*, paper_id: str, repo_id: int) -> SimpleNamespace:
        return {"a": spec_a, "b": spec_b}[paper_id]

    spec_merge._spec_repo.get_by_paper_id.side_effect = get_by_paper_id
    commit = _commit(repo_id=3, sha="sha")

    spec_merge.merge_specs(
        commit=commit,
        changes=GitCommitPathInformation(
            paths=[
                _spec_change("specs/a/spec.md"),
                _spec_change("specs/b/plan.md"),
            ]
        ),
    )

    first, second = spec_merge._spec_extraction_agent.extract_spec.call_args_list
    assert first.kwargs == {"spec_md": "SA", "tasks_md": None, "plan_md": None}
    assert second.kwargs == {"spec_md": "SB", "tasks_md": None, "plan_md": "PB"}
