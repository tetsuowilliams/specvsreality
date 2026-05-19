"""Tests for ``BlobRepo``."""

from __future__ import annotations

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import BlobRepo


def test_upsert_inserts_when_missing(db_session: Session) -> None:
    blobs = BlobRepo(db_session)
    sha = "a" * 40
    blobs.upsert(sha=sha, size_bytes=12)
    row = blobs.get(sha)
    assert row is not None
    assert row.size_bytes == 12


def test_upsert_is_idempotent_on_conflict(db_session: Session) -> None:
    blobs = BlobRepo(db_session)
    sha = "b" * 40
    blobs.upsert(sha=sha, size_bytes=10)
    blobs.upsert(sha=sha, size_bytes=999)
    row = blobs.get(sha)
    assert row is not None
    assert row.size_bytes == 10


def test_exists_reflects_state(db_session: Session) -> None:
    blobs = BlobRepo(db_session)
    sha = "c" * 40
    assert blobs.exists(sha) is False
    blobs.upsert(sha=sha, size_bytes=None)
    assert blobs.exists(sha) is True


def test_all_shas_returns_set(db_session: Session) -> None:
    blobs = BlobRepo(db_session)
    blobs.upsert(sha="d" * 40, size_bytes=1)
    blobs.upsert(sha="e" * 40, size_bytes=2)
    out = blobs.all_shas()
    assert {"d" * 40, "e" * 40}.issubset(out)
