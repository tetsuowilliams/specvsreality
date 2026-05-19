"""Blob (content-addressed) access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from specvsreality_repositories.models.blob import Blob


class BlobRepo:
    """Read/write access for the ``blobs`` table.

    ``upsert`` is idempotent on the primary key (``sha``) so the ingestion pipeline
    can write the same blob from many commits without conflict.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert(
        self, *, sha: str, size_bytes: int | None, storage_url: str | None = None
    ) -> None:
        stmt = (
            insert(Blob)
            .values(sha=sha, size_bytes=size_bytes, storage_url=storage_url)
            .on_conflict_do_nothing(index_elements=["sha"])
        )
        self._session.execute(stmt)

    def exists(self, sha: str) -> bool:
        stmt = select(Blob.sha).where(Blob.sha == sha).limit(1)
        return self._session.scalars(stmt).first() is not None

    def get(self, sha: str) -> Blob | None:
        return self._session.get(Blob, sha)

    def all_shas(self) -> set[str]:
        stmt = select(Blob.sha)
        return set(self._session.scalars(stmt).all())


def create_blob_repo(session: Session) -> BlobRepo:
    return BlobRepo(session)
