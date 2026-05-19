"""Tests for ``IngestionService`` orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from specvsreality_repositories.models.repository import Repository
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_worker.domain import CommitRecord, TreeEntry
from specvsreality_worker.ingestion import IngestionService


def _repo() -> Repository:
    return Repository(id=10, name="r", url="https://r", default_branch="main")


def _commits(n: int) -> list[CommitRecord]:
    base = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        CommitRecord(
            sha=f"{i + 1}" * 40,
            repository_id=10,
            commit_date=base + timedelta(days=i),
        )
        for i in range(n)
    ]


def test_processes_each_commit_in_order_and_calls_callback() -> None:
    commits = _commits(3)
    git_client = MagicMock()
    git_client.iter_commits.return_value = iter(commits)
    commit_processor = MagicMock()
    commit_processor.process.side_effect = lambda **_: [
        TreeEntry(path="x.py", blob_sha="0" * 40, size_bytes=10)
    ]
    spec_sync = MagicMock()
    spec_sync.process.return_value = []
    evaluation = MagicMock()

    seen: list[str] = []

    service = IngestionService(
        git_client=git_client,
        repository_repo=MagicMock(),
        commit_processor=commit_processor,
        spec_sync_step=spec_sync,
        evaluation_step=evaluation,
    )
    service.ingest_repo(repository=_repo(), after_commit=lambda c: seen.append(c.sha))

    assert [c.sha for c in commits] == seen
    assert commit_processor.process.call_count == 3
    assert spec_sync.process.call_count == 3
    assert evaluation.process.call_count == 3


def test_runs_retroactive_backfill_for_each_new_requirement_version() -> None:
    commits = _commits(2)
    git_client = MagicMock()
    git_client.iter_commits.return_value = iter(commits)
    commit_processor = MagicMock()
    commit_processor.process.return_value = []

    rv_first = MagicMock(spec=RequirementVersion, id=1)
    rv_second = MagicMock(spec=RequirementVersion, id=2)

    spec_sync = MagicMock()
    spec_sync.process.side_effect = [[rv_first], [rv_second]]
    evaluation = MagicMock()
    backfill = MagicMock()

    service = IngestionService(
        git_client=git_client,
        repository_repo=MagicMock(),
        commit_processor=commit_processor,
        spec_sync_step=spec_sync,
        evaluation_step=evaluation,
        retroactive_backfill_service=backfill,
    )
    service.ingest_repo(repository=_repo())

    assert backfill.backfill.call_count == 2
    backfill.backfill.assert_any_call(requirement_version=rv_first)
    backfill.backfill.assert_any_call(requirement_version=rv_second)
