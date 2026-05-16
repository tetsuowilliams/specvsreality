"""Repos route tests."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from specvsreality_api.main import create_app
from specvsreality_api.routes import health, repos
from specvsreality_repositories.models import Base
from specvsreality_repositories.models.git_repo import GitRepo


class CapturePublisher:
    def __init__(self) -> None:
        self.bodies: list[bytes] = []

    async def publish(self, body: bytes, _settings: object) -> None:
        self.bodies.append(body)


@pytest.fixture
def repos_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[FastAPI, CapturePublisher, Engine]:
    db_path = tmp_path / "api-test.db"
    db_url = f"sqlite:///{db_path}"
    monkeypatch.setenv("DATABASE_URL", db_url)

    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__])

    app = create_app()
    cap = CapturePublisher()

    def _session_override() -> Generator[Session, None, None]:
        session = Session(bind=engine)
        try:
            yield session
        finally:
            session.close()

    async def _noop_rabbit() -> None:
        return None

    app.dependency_overrides[health.verify_rabbit_reachable] = _noop_rabbit
    app.dependency_overrides[repos.get_publisher] = lambda: cap
    app.dependency_overrides[repos.get_session] = _session_override
    return app, cap, engine


def test_create_and_list_repos(repos_app: tuple[FastAPI, CapturePublisher, Engine]) -> None:
    app, cap, _ = repos_app
    with TestClient(app) as client:
        create = client.post("/repos", json={"name": "repo-a", "url": "https://example.test/repo-a.git"})
        assert create.status_code == 200
        payload = create.json()
        assert payload["queued"] is True
        assert payload["repo"]["name"] == "repo-a"
        assert payload["repo"]["location"] == ""
        assert payload["repo"]["cursor_position"] == ""

        listing = client.get("/repos")
        assert listing.status_code == 200
        rows = listing.json()
        assert len(rows) == 1
        assert rows[0]["name"] == "repo-a"
        assert rows[0]["url"] == "https://example.test/repo-a.git"

    assert len(cap.bodies) == 1
    assert b'"message_type":"scan_repo"' in cap.bodies[0]


def test_get_repo_by_id(repos_app: tuple[FastAPI, CapturePublisher, Engine]) -> None:
    app, _, _ = repos_app
    with TestClient(app) as client:
        create = client.post("/repos", json={"name": "repo-a", "url": "https://example.test/repo-a.git"})
        assert create.status_code == 200
        repo_id = create.json()["repo"]["id"]

        got = client.get(f"/repos/{repo_id}")
        assert got.status_code == 200
        body = got.json()
        assert body["id"] == repo_id
        assert body["name"] == "repo-a"

        missing = client.get("/repos/999999999")
        assert missing.status_code == 404
