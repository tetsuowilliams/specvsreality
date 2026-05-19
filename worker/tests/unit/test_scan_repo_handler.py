"""Unit tests for ``ScanRepoHandler`` orchestration glue."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine, text

from specvsreality_messages import ScanRepoMessage
from specvsreality_worker.handlers.scan_repo import (
    ScanRepoHandler,
    _clone_url_with_optional_token,
)


def test_constructor_rejects_null_factory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must not be None"):
        ScanRepoHandler(clone_root=tmp_path, ingestion_service_factory=None)  # type: ignore[arg-type]


def test_clone_url_uses_token_for_https(monkeypatch) -> None:
    monkeypatch.setenv("GIT_CLONE_TOKEN", "secret-token")
    monkeypatch.delenv("GIT_CLONE_USERNAME", raising=False)
    url = _clone_url_with_optional_token("https://github.com/org/repo.git")
    assert url == "https://x-access-token:secret-token@github.com/org/repo.git"


def test_clone_url_keeps_original_when_credentials_already_present(monkeypatch) -> None:
    monkeypatch.setenv("GIT_CLONE_TOKEN", "secret-token")
    original = "https://alice:abc@github.com/org/repo.git"
    assert _clone_url_with_optional_token(original) == original


def test_handle_clones_invokes_ingestion_and_advances_cursor(
    tmp_path: Path, monkeypatch
) -> None:
    """End-to-end with a fake ``IngestionService``: confirms wiring + cursor update."""
    from fixtures.git_repos import make_linear_three_commit_repo

    source_path, shas = make_linear_three_commit_repo(tmp_path, use_main=True)

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE repositories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT NOT NULL,
                    default_branch TEXT NOT NULL DEFAULT 'main',
                    clone_location TEXT,
                    cursor_position TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO repositories (name, url) VALUES (:name, :url)"
            ),
            {"name": "src", "url": str(source_path)},
        )
        repository_id = conn.execute(
            text("SELECT id FROM repositories LIMIT 1")
        ).scalar_one()

    monkeypatch.setenv("DATABASE_URL", db_url)

    captured = {"calls": 0}

    def _factory(_session, git_client) -> object:
        service = MagicMock()

        def fake_ingest(*, repository, after_commit):
            captured["calls"] += 1
            for record in git_client.iter_commits(oldest_first=True):
                if after_commit is not None:
                    after_commit(record)

        service.ingest_repo.side_effect = fake_ingest
        return service

    handler = ScanRepoHandler(
        clone_root=tmp_path / "clones",
        ingestion_service_factory=_factory,
    )
    handler.handle(ScanRepoMessage(repo_id=str(repository_id)))

    with engine.begin() as conn:
        cursor_sha = conn.execute(
            text("SELECT cursor_position FROM repositories WHERE id = :id"),
            {"id": int(repository_id)},
        ).scalar_one()
        clone_location = conn.execute(
            text("SELECT clone_location FROM repositories WHERE id = :id"),
            {"id": int(repository_id)},
        ).scalar_one()

    assert captured["calls"] == 1
    assert cursor_sha == shas[-1]
    assert clone_location == str((tmp_path / "clones" / str(repository_id)).resolve())
