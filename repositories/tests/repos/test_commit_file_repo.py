"""Tests for ``CommitFileRepo``."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    BlobRepo,
    CommitFileRepo,
    CommitRepo,
)


@pytest.fixture()
def commit_sha(db_session: Session, repository_id: int) -> str:
    sha = "c" * 40
    CommitRepo(db_session).insert(
        sha=sha,
        repository_id=repository_id,
        commit_date=datetime.now(UTC),
    )
    return sha


def test_insert_many_and_paths_at_commit(
    db_session: Session, commit_sha: str
) -> None:
    blobs = BlobRepo(db_session)
    blob_a = "a" * 40
    blob_b = "b" * 40
    blobs.upsert(sha=blob_a, size_bytes=1)
    blobs.upsert(sha=blob_b, size_bytes=2)

    files = CommitFileRepo(db_session)
    files.insert_many(
        commit_sha=commit_sha,
        entries=[("src/app.py", blob_a, "100644"), ("README.md", blob_b, "100644")],
    )

    paths = files.paths_at_commit(commit_sha)
    assert [p.path for p in paths] == ["README.md", "src/app.py"]


def test_blob_at_returns_sha_or_none(db_session: Session, commit_sha: str) -> None:
    blob = "a" * 40
    BlobRepo(db_session).upsert(sha=blob, size_bytes=1)
    files = CommitFileRepo(db_session)
    files.insert_many(commit_sha=commit_sha, entries=[("src/x.py", blob, None)])

    assert files.blob_at(commit_sha=commit_sha, path="src/x.py") == blob
    assert files.blob_at(commit_sha=commit_sha, path="missing.py") is None


def test_code_blobs_at_commit_excludes_paths(
    db_session: Session, commit_sha: str
) -> None:
    blobs = BlobRepo(db_session)
    spec_blob = "1" * 40
    code_blob = "2" * 40
    blobs.upsert(sha=spec_blob, size_bytes=10)
    blobs.upsert(sha=code_blob, size_bytes=20)

    files = CommitFileRepo(db_session)
    files.insert_many(
        commit_sha=commit_sha,
        entries=[
            ("specs/auth/spec.md", spec_blob, None),
            ("src/auth.py", code_blob, None),
        ],
    )

    out = files.code_blobs_at_commit(
        commit_sha=commit_sha, exclude_paths={"specs/auth/spec.md"}
    )
    assert out == {code_blob}
