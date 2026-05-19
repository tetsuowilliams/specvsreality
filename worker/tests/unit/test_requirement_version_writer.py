"""Tests for ``RequirementVersionWriter`` (idempotency by (req, spec_version))."""

from __future__ import annotations

from unittest.mock import MagicMock

from specvsreality_repositories.models.requirement import Requirement
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_worker.domain import ExtractedRequirement
from specvsreality_worker.spec import RequirementVersionWriter
from specvsreality_worker.support import HashUtil


def _spec_version() -> SpecVersion:
    return SpecVersion(
        id=10,
        spec_id=1,
        spec_blob_sha="a" * 40,
        plan_blob_sha="b" * 40,
        tasks_blob_sha="c" * 40,
        first_seen_commit="d" * 40,
        first_seen_at=None,  # not used by the writer
    )


def test_returns_existing_row_without_inserting() -> None:
    requirement_repo = MagicMock()
    requirement_version_repo = MagicMock()
    requirement_repo.get_or_create.return_value = MagicMock(
        spec=Requirement, id=42, spec_id=1
    )
    existing = MagicMock(spec=RequirementVersion)
    requirement_version_repo.get_for_pair.return_value = existing

    writer = RequirementVersionWriter(
        requirement_repo=requirement_repo,
        requirement_version_repo=requirement_version_repo,
        hash_util=HashUtil(),
    )
    out = writer.write(
        spec_version=_spec_version(),
        extracted=ExtractedRequirement(external_id="FR-001", content="do x"),
        extraction_model="m",
        extraction_prompt="p",
    )
    assert out is existing
    requirement_version_repo.insert.assert_not_called()


def test_inserts_when_pair_is_new() -> None:
    requirement_repo = MagicMock()
    requirement_version_repo = MagicMock()
    requirement_repo.get_or_create.return_value = MagicMock(
        spec=Requirement, id=42, spec_id=1
    )
    requirement_version_repo.get_for_pair.return_value = None
    inserted = MagicMock(spec=RequirementVersion)
    requirement_version_repo.insert.return_value = inserted

    writer = RequirementVersionWriter(
        requirement_repo=requirement_repo,
        requirement_version_repo=requirement_version_repo,
        hash_util=HashUtil(),
    )
    out = writer.write(
        spec_version=_spec_version(),
        extracted=ExtractedRequirement(
            external_id="FR-001",
            content="do x",
            path_globs=("src/**/*.py", "tests/**/*"),
        ),
        extraction_model="model-v1",
        extraction_prompt="prompt-v1",
    )
    assert out is inserted
    insert_kwargs = requirement_version_repo.insert.call_args.kwargs
    assert insert_kwargs["requirement_id"] == 42
    assert insert_kwargs["spec_version_id"] == 10
    assert insert_kwargs["content"] == "do x"
    assert insert_kwargs["extraction_model"] == "model-v1"
    assert len(insert_kwargs["content_hash"]) == 40
    assert insert_kwargs["path_globs"] == ["src/**/*.py", "tests/**/*"]


def test_inserts_with_empty_path_globs_when_extractor_provides_none() -> None:
    requirement_repo = MagicMock()
    requirement_version_repo = MagicMock()
    requirement_repo.get_or_create.return_value = MagicMock(
        spec=Requirement, id=42, spec_id=1
    )
    requirement_version_repo.get_for_pair.return_value = None
    requirement_version_repo.insert.return_value = MagicMock(spec=RequirementVersion)

    writer = RequirementVersionWriter(
        requirement_repo=requirement_repo,
        requirement_version_repo=requirement_version_repo,
        hash_util=HashUtil(),
    )
    writer.write(
        spec_version=_spec_version(),
        extracted=ExtractedRequirement(external_id="FR-001", content="do x"),
        extraction_model="m",
        extraction_prompt="p",
    )
    assert requirement_version_repo.insert.call_args.kwargs["path_globs"] == []
