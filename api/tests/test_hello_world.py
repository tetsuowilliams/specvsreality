"""Hello-world HTTP → queue contract (publisher mocked)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from specvsreality_api.config import Settings
from specvsreality_api.main import create_app
from specvsreality_api.routes import health, hello_world


class CapturePublisher:
    def __init__(self) -> None:
        self.bodies: list[bytes] = []

    async def publish(self, body: bytes, settings: Settings) -> None:
        self.bodies.append(body)


@pytest.fixture
def capture_app() -> tuple[FastAPI, CapturePublisher]:
    app = create_app()
    cap = CapturePublisher()

    async def _noop_rabbit() -> None:
        return None

    app.dependency_overrides[health.verify_rabbit_reachable] = _noop_rabbit
    app.dependency_overrides[hello_world.get_publisher] = lambda: cap
    return app, cap


def test_post_hello_world_queues_json(capture_app: tuple[FastAPI, CapturePublisher]) -> None:
    app, cap = capture_app
    with TestClient(app) as client:
        r = client.post("/hello-world", json={"name": "TestUser"})
    assert r.status_code == 200
    assert r.json() == {"queued": True}
    assert len(cap.bodies) == 1
    assert b'"message_type":"hello_world"' in cap.bodies[0]
    assert b'"name":"TestUser"' in cap.bodies[0]


def test_health_ok(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
