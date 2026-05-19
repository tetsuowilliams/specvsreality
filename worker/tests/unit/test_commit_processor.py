"""Tests for ``CommitProcessor`` idempotency + tree persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from specvsreality_repositories.models.repository import Repository
from specvsreality_worker.domain import CommitRecord, ParentRef, TreeEntry
from specvsreality_worker.ingestion import CommitProcessor


def _repo() -> Repository:
    return Repository(id=10, name="r", url="https://r", default_branch="main")


def _commit() -> CommitRecord:
    return CommitRecord(
        sha="1" * 40,
        repository_id=10,
        commit_date=datetime.now(UTC),
        parent_shas=[ParentRef(parent_sha="0" * 40, parent_order=0)],
        author_name="Ada",
        message="init",
    )


def test_persists_commit_blobs_and_files_on_first_sight() -> None:
    git_client = MagicMock()
    tree = [
        TreeEntry(path="a.py", blob_sha="a" * 40, size_bytes=10, mode="100644"),
        TreeEntry(path="b.py", blob_sha="b" * 40, size_bytes=20),
    ]
    git_client.list_tree.return_value = tree
    commit_repo = MagicMock()
    commit_repo.exists.return_value = False
    blob_repo = MagicMock()
    commit_file_repo = MagicMock()

    processor = CommitProcessor(
        git_client=git_client,
        commit_repo=commit_repo,
        blob_repo=blob_repo,
        commit_file_repo=commit_file_repo,
    )
    out = processor.process(repository=_repo(), commit=_commit())
    assert out == tree

    commit_repo.insert.assert_called_once()
    commit_repo.insert_parents.assert_called_once()
    assert blob_repo.upsert.call_count == 2
    commit_file_repo.insert_many.assert_called_once()


def test_skips_persistence_when_commit_already_exists() -> None:
    git_client = MagicMock()
    git_client.list_tree.return_value = []
    commit_repo = MagicMock()
    commit_repo.exists.return_value = True
    blob_repo = MagicMock()
    commit_file_repo = MagicMock()

    processor = CommitProcessor(
        git_client=git_client,
        commit_repo=commit_repo,
        blob_repo=blob_repo,
        commit_file_repo=commit_file_repo,
    )
    processor.process(repository=_repo(), commit=_commit())

    commit_repo.insert.assert_not_called()
    commit_repo.insert_parents.assert_not_called()
    blob_repo.upsert.assert_not_called()
    commit_file_repo.insert_many.assert_not_called()
