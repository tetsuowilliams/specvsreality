"""Unit tests for `RequirementMerge` (repos mocked)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from specvsreality_repositories.repos.enums import VersionStatus
from specvsreality_worker.agents.spec_extraction_agent.models import ParsedRequirement, SpecExtractionResult
from specvsreality_worker.core import CommitContext, RequirementMerge


@pytest.fixture
def commit() -> CommitContext:
    return CommitContext(
        repo_id=1,
        commit_sha="c0ffee",
        commit_datetime=datetime(2026, 1, 1, tzinfo=UTC),
    )


@pytest.fixture
def db_spec() -> SimpleNamespace:
    return SimpleNamespace(id=42)


@pytest.fixture
def requirement_merge() -> RequirementMerge:
    tree_scan = MagicMock()
    tree_scan.scan_tree.return_value = []
    return RequirementMerge(
        requirement_repo=MagicMock(),
        requirement_version_repo=MagicMock(),
        tree_scan=tree_scan,
    )


def test_merge_creates_requirement_and_version_when_not_in_db(
    requirement_merge: RequirementMerge,
    db_spec: SimpleNamespace,
    commit: CommitContext,
) -> None:
    requirement_merge._requirement_repo.get_by_spec_and_paper_id.return_value = None
    requirement_merge._requirement_repo.list_latest_active_for_spec.return_value = []
    requirement_merge._requirement_version_repo.get_latest_for_requirement.return_value = None
    new_row = SimpleNamespace(id=100)
    requirement_merge._requirement_repo.add.return_value = new_row
    new_rv = SimpleNamespace(id=200)
    requirement_merge._requirement_version_repo.add.return_value = new_rv

    extracted = SpecExtractionResult(
        spec_title="S",
        functional_requirements=[
            ParsedRequirement(id="FR-1", text="Do the thing", path_globs=["*.py"]),
        ],
    )

    requirement_merge.merge_requirements(db_spec=db_spec, extracted_spec=extracted, commit=commit)

    requirement_merge._requirement_repo.add.assert_called_once_with(spec_id=42, paper_id="FR-1")
    requirement_merge._requirement_version_repo.add.assert_called_once()
    call = requirement_merge._requirement_version_repo.add.call_args
    assert call.kwargs["requirement_id"] == 100
    assert call.kwargs["commit_sha"] == commit.commit_sha
    assert call.kwargs["commit_datetime"] == commit.commit_datetime
    assert call.kwargs["requirement_text"] == "Do the thing"
    assert call.kwargs["filepath_globs"] == ["*.py"]
    assert call.kwargs["status"] == VersionStatus.ACTIVE.value


def test_merge_does_not_add_version_when_text_unchanged(
    requirement_merge: RequirementMerge,
    db_spec: SimpleNamespace,
    commit: CommitContext,
) -> None:
    existing = SimpleNamespace(id=10, paper_id="FR-1")
    requirement_merge._requirement_repo.get_by_spec_and_paper_id.return_value = existing
    latest = SimpleNamespace(requirement_text="same body")
    requirement_merge._requirement_version_repo.get_latest_for_requirement.return_value = latest
    requirement_merge._requirement_repo.list_latest_active_for_spec.return_value = [existing]

    extracted = SpecExtractionResult(
        spec_title="S",
        functional_requirements=[
            ParsedRequirement(id="FR-1", text="same body", path_globs=[]),
        ],
    )

    requirement_merge.merge_requirements(db_spec=db_spec, extracted_spec=extracted, commit=commit)

    requirement_merge._requirement_repo.add.assert_not_called()
    requirement_merge._requirement_version_repo.add.assert_not_called()


def test_merge_adds_updated_version_when_text_changes(
    requirement_merge: RequirementMerge,
    db_spec: SimpleNamespace,
    commit: CommitContext,
) -> None:
    existing = SimpleNamespace(id=10, paper_id="FR-1")
    requirement_merge._requirement_repo.get_by_spec_and_paper_id.return_value = existing
    requirement_merge._requirement_version_repo.get_latest_for_requirement.return_value = SimpleNamespace(
        requirement_text="old"
    )
    requirement_merge._requirement_repo.list_latest_active_for_spec.return_value = [existing]
    new_rv = SimpleNamespace(id=300)
    requirement_merge._requirement_version_repo.add.return_value = new_rv

    extracted = SpecExtractionResult(
        spec_title="S",
        functional_requirements=[
            ParsedRequirement(id="FR-1", text="new", path_globs=["a/*.py"]),
        ],
    )

    requirement_merge.merge_requirements(db_spec=db_spec, extracted_spec=extracted, commit=commit)

    requirement_merge._requirement_version_repo.add.assert_called_once()
    call = requirement_merge._requirement_version_repo.add.call_args
    assert call.kwargs["requirement_id"] == 10
    assert call.kwargs["commit_sha"] == commit.commit_sha
    assert call.kwargs["requirement_text"] == "new"
    assert call.kwargs["status"] == VersionStatus.UPDATED.value


def test_merge_marks_missing_requirement_inactive(
    requirement_merge: RequirementMerge,
    db_spec: SimpleNamespace,
    commit: CommitContext,
) -> None:
    gone = SimpleNamespace(id=55, paper_id="FR-GONE")
    requirement_merge._requirement_repo.list_latest_active_for_spec.return_value = [gone]

    extracted = SpecExtractionResult(spec_title="S", functional_requirements=[])

    requirement_merge.merge_requirements(db_spec=db_spec, extracted_spec=extracted, commit=commit)

    requirement_merge._requirement_version_repo.add.assert_called_once()
    call = requirement_merge._requirement_version_repo.add.call_args
    assert call.kwargs["requirement_id"] == 55
    assert call.kwargs["commit_sha"] == commit.commit_sha
    assert call.kwargs["requirement_text"] == ""
    assert call.kwargs["filepath_globs"] == []
    assert call.kwargs["status"] == VersionStatus.INACTIVE.value
