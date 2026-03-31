"""Shared fixtures."""

from __future__ import annotations

import pytest

from specvsreality_worker.config import WorkerSettings


@pytest.fixture
def worker_settings() -> WorkerSettings:
    return WorkerSettings(
        host="localhost",
        port=5672,
        virtual_host="/",
        queue_name="messages",
        prefetch_count=1,
        username="guest",
        password="guest",
    )
