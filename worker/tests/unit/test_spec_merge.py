"""Unit tests for `SpecMerge` (Stage 2)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.repos.enums import VersionStatus
from specvsreality_worker.agents.spec_extraction_agent.models import (
    ExtractedSpec,
    ExtractedSpecItem,
)
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.spec_detection import ArtifactType, SpecDetection
from specvsreality_worker.core.spec_merge import SpecMerge
from specvsreality_worker.git_adapter import ChangedPath, GitCommitPathInformation, PathChangeState


class FakeGitAdapter:
    """Dict-backed git reads for orchestration tests."""

    def __init__(self, contents: dict[str, str]) -> None:
        self._contents = {k.replace("\\", "/"): v for k, v in contents.items()}
        self.calls: list[tuple[str, str]] = []

    def file_at_commit_or_none(self, commit_sha: str, relpath: str) -> str | None:
        key = relpath.replace("\\", "/")
        self.calls.append((commit_sha, key))
        return self._contents.get(key)


def _spec_change(path: str, state: PathChangeState = PathChangeState.MODIFIED) -> ChangedPath:
    return ChangedPath(path=path, state=state, artifact_type=ArtifactType.SPEC)


def _code_change(path: str, state: PathChangeState = PathChangeState.NEW) -> ChangedPath:
    return ChangedPath(path=path, state=state, artifact_type=ArtifactType.CODE)


def _make_spec_merge(fake_git: FakeGitAdapter) -> SpecMerge:
    spec_merge = SpecMerge(
        spec_repo=MagicMock(),
        spec_version_repo=MagicMock(),
        spec_item_repo=MagicMock(),
        spec_extraction_agent=MagicMock(),
        git_adapter=fake_git,
        spec_detection=SpecDetection(),
    )
    spec_merge._spec_version_repo.add.return_value = SimpleNamespace(id=900)
    spec_merge._spec_item_repo.add.return_value = SimpleNamespace(id=1)
    spec_merge._spec_item_repo.list_for_spec_version.return_value = []
    return spec_merge


def _commit(*, repo_id: int = 1, sha: str = "abc123", commit_id: int = 5) -> CommitContext:
    return CommitContext(
        repo_id=repo_id,
        commit_id=commit_id,
        commit_sha=sha,
        commit_datetime=datetime(2026, 3, 1, tzinfo=UTC),
        commit_message="msg",
    )


def _extracted(items: list[ExtractedSpecItem] | None = None) -> ExtractedSpec:
    return ExtractedSpec(title="Title", summary="Summary", items=items or [])


def test_merge_specs_empty_changes_returns_empty() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)

    works = spec_merge.merge_specs(commit=_commit(), changes=GitCommitPathInformation(paths=[]))

    assert works == []
    assert fake_git.calls == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()
    spec_merge._spec_version_repo.get_or_create.assert_not_called()


def test_merge_specs_creates_version_and_items() -> None:
    fake_git = FakeGitAdapter(
        {
            "specs/0001-a/spec.md": "# Spec\n",
            "specs/0001-a/tasks.md": "- [ ] Task\n",
            "specs/0001-a/plan.md": "## Plan\n",
        }
    )
    spec_merge = _make_spec_merge(fake_git)
    item = ExtractedSpecItem(
        local_key="FR-1",
        item_type="functional_behavior",
        text="Greets users",
        source_quote="greets",
        importance="must",
        success_criteria=["prints hello"],
        failure_criteria=["no output"],
    )
    spec_merge._spec_extraction_agent.extract_spec.return_value = _extracted([item])
    spec_merge._spec_repo.get_or_create_for_folder.return_value = (SimpleNamespace(id=501), True)
    spec_merge._spec_version_repo.get_or_create.return_value = (SimpleNamespace(id=900), True)
    commit = _commit(sha="abc123", commit_id=9)

    works = spec_merge.merge_specs(
        commit=commit,
        changes=GitCommitPathInformation(paths=[_spec_change("specs/0001-a/spec.md")]),
    )

    spec_merge._spec_repo.get_or_create_for_folder.assert_called_once_with(
        folder="specs/0001-a",
        repo_id=1,
    )
    spec_merge._spec_version_repo.get_or_create.assert_called_once()
    get_or_create_kwargs = spec_merge._spec_version_repo.get_or_create.call_args.kwargs
    assert get_or_create_kwargs["spec_id"] == 501
    assert get_or_create_kwargs["commit_id"] == 9
    spec_merge._spec_item_repo.add.assert_called_once_with(
        spec_version_id=900,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="Greets users",
        source_quote="greets",
        importance=SpecItemImportance.MUST,
        success_criteria=["prints hello"],
        failure_criteria=["no output"],
        highlight_spans={"spec": None, "tasks": None, "plan": None},
    )
    assert len(works) == 1
    assert works[0].spec_label == "specs/0001-a"
    assert len(works[0].spec_items) == 1


def test_merge_specs_deduplicates_spec_folder() -> None:
    fake_git = FakeGitAdapter(
        {
            "specs/0001-a/spec.md": "S",
            "specs/0001-a/tasks.md": "T",
        }
    )
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._spec_extraction_agent.extract_spec.return_value = _extracted()
    spec_merge._spec_repo.get_or_create_for_folder.return_value = (SimpleNamespace(id=2), False)
    spec_merge._spec_version_repo.get_or_create.return_value = (SimpleNamespace(id=900), True)

    spec_merge.merge_specs(
        commit=_commit(),
        changes=GitCommitPathInformation(
            paths=[
                _spec_change("specs/0001-a/spec.md"),
                _spec_change("specs/0001-a/tasks.md"),
            ]
        ),
    )

    assert spec_merge._spec_extraction_agent.extract_spec.call_count == 1
    assert spec_merge._spec_version_repo.get_or_create.call_count == 1


def test_merge_specs_creates_spec_when_missing() -> None:
    fake_git = FakeGitAdapter({"specs/x/spec.md": "body"})
    spec_merge = _make_spec_merge(fake_git)
    spec_merge._spec_extraction_agent.extract_spec.return_value = _extracted()
    spec_merge._spec_repo.get_or_create_for_folder.return_value = (SimpleNamespace(id=77), True)
    spec_merge._spec_version_repo.get_or_create.return_value = (SimpleNamespace(id=900), True)

    spec_merge.merge_specs(
        commit=_commit(),
        changes=GitCommitPathInformation(paths=[_spec_change("specs/x/spec.md", PathChangeState.NEW)]),
    )

    spec_merge._spec_repo.get_or_create_for_folder.assert_called_once_with(
        folder="specs/x",
        repo_id=1,
    )


def test_merge_spec_folder_reuses_existing_version() -> None:
    fake_git = FakeGitAdapter({"specs/x/spec.md": "body"})
    spec_merge = _make_spec_merge(fake_git)
    existing_version = SimpleNamespace(
        id=42,
        spec_md="body",
        tasks_md=None,
        plan_md=None,
    )
    existing_items = [SimpleNamespace(id=7)]
    spec_merge._spec_repo.get_or_create_for_folder.return_value = (SimpleNamespace(id=5), False)
    spec_merge._spec_version_repo.get_or_create.return_value = (existing_version, False)
    spec_merge._spec_item_repo.list_for_spec_version.return_value = existing_items

    work = spec_merge.merge_spec_folder(commit=_commit(), folder="specs/x")

    assert work is not None
    assert work.spec_version is existing_version
    assert work.spec_items == existing_items
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()
    spec_merge._spec_item_repo.add.assert_not_called()


def test_merge_specs_skips_when_spec_md_absent() -> None:
    fake_git = FakeGitAdapter({"specs/x/tasks.md": "T"})
    spec_merge = _make_spec_merge(fake_git)

    works = spec_merge.merge_specs(
        commit=_commit(),
        changes=GitCommitPathInformation(paths=[_spec_change("specs/x/tasks.md")]),
    )

    assert works == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()
    spec_merge._spec_version_repo.get_or_create.assert_not_called()


def test_merge_specs_ignores_code_paths() -> None:
    fake_git = FakeGitAdapter({})
    spec_merge = _make_spec_merge(fake_git)

    works = spec_merge.merge_specs(
        commit=_commit(),
        changes=GitCommitPathInformation(
            paths=[_code_change("README.md"), _code_change("src/main.py")]
        ),
    )

    assert works == []
    assert fake_git.calls == []
    spec_merge._spec_extraction_agent.extract_spec.assert_not_called()
