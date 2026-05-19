"""Commit -> path -> blob mappings."""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.commit_file import CommitFile


class CommitFileRepo:
    """Read/write access for the ``commit_files`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def insert_many(
        self,
        *,
        commit_sha: str,
        entries: Iterable[tuple[str, str, str | None]],
    ) -> None:
        """``entries`` is an iterable of ``(path, blob_sha, mode)`` tuples."""
        rows = [
            CommitFile(
                commit_sha=commit_sha,
                path=path,
                blob_sha=blob_sha,
                mode=mode,
            )
            for path, blob_sha, mode in entries
        ]
        if not rows:
            return
        self._session.add_all(rows)
        self._session.flush()

    def paths_at_commit(self, commit_sha: str) -> list[CommitFile]:
        stmt = (
            select(CommitFile)
            .where(CommitFile.commit_sha == commit_sha)
            .order_by(CommitFile.path.asc())
        )
        return list(self._session.scalars(stmt).all())

    def blob_at(self, *, commit_sha: str, path: str) -> str | None:
        stmt = select(CommitFile.blob_sha).where(
            CommitFile.commit_sha == commit_sha,
            CommitFile.path == path,
        )
        return self._session.scalars(stmt).first()

    def code_blobs_at_commit(
        self, *, commit_sha: str, exclude_paths: set[str]
    ) -> set[str]:
        """Distinct blob SHAs at a commit, excluding any paths in ``exclude_paths``."""
        stmt = select(CommitFile.blob_sha, CommitFile.path).where(
            CommitFile.commit_sha == commit_sha
        )
        return {
            blob_sha
            for blob_sha, path in self._session.execute(stmt).all()
            if path not in exclude_paths
        }


def create_commit_file_repo(session: Session) -> CommitFileRepo:
    return CommitFileRepo(session)
