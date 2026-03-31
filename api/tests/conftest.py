"""Test app and dependency overrides."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from specvsreality_api.main import create_app
from specvsreality_api.routes import health


@pytest.fixture
def client() -> TestClient:
    app = create_app()

    async def _noop_rabbit() -> None:
        return None

    app.dependency_overrides[health.verify_rabbit_reachable] = _noop_rabbit
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
