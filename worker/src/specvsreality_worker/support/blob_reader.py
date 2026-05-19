"""Cached blob -> text reader bridging ``GitClient`` to higher layers."""

from __future__ import annotations

from specvsreality_worker.git import GitClient, GitClientError


class BlobReaderError(Exception):
    """Raised when blob bytes cannot be decoded as UTF-8 text."""


class BlobReader:
    """Reads blob content as text, caching results within a run.

    The cache is intentionally process-local: ingestion is a short-lived job
    where the same blob is read many times (e.g. one blob across all commits
    that contain it). Memory bounds are the responsibility of the caller --
    blobs are typically source files, not large binaries.
    """

    def __init__(self, *, git_client: GitClient) -> None:
        self._git = git_client
        self._cache: dict[str, str] = {}

    def read_text(self, blob_sha: str) -> str:
        cached = self._cache.get(blob_sha)
        if cached is not None:
            return cached
        try:
            raw = self._git.read_blob(blob_sha)
        except GitClientError as exc:
            raise BlobReaderError(f"failed to read blob {blob_sha!r}") from exc
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise BlobReaderError(
                f"blob {blob_sha!r} is not valid UTF-8 text"
            ) from exc
        self._cache[blob_sha] = text
        return text
