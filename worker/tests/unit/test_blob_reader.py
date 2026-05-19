"""Tests for ``BlobReader``."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from specvsreality_worker.git import GitClient, GitClientError
from specvsreality_worker.support import BlobReader
from specvsreality_worker.support.blob_reader import BlobReaderError


def test_caches_repeated_reads() -> None:
    git_client = MagicMock(spec=GitClient)
    git_client.read_blob.return_value = b"hello"
    reader = BlobReader(git_client=git_client)

    assert reader.read_text("a" * 40) == "hello"
    assert reader.read_text("a" * 40) == "hello"
    git_client.read_blob.assert_called_once()


def test_raises_blob_reader_error_for_invalid_utf8() -> None:
    git_client = MagicMock(spec=GitClient)
    git_client.read_blob.return_value = b"\xff\xfeinvalid"
    reader = BlobReader(git_client=git_client)

    with pytest.raises(BlobReaderError, match="not valid UTF-8"):
        reader.read_text("b" * 40)


def test_propagates_git_client_error_as_blob_reader_error() -> None:
    git_client = MagicMock(spec=GitClient)
    git_client.read_blob.side_effect = GitClientError("missing")
    reader = BlobReader(git_client=git_client)

    with pytest.raises(BlobReaderError, match="failed to read blob"):
        reader.read_text("c" * 40)
