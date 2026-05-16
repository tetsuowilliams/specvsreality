"""Worker test defaults."""

from __future__ import annotations

import pytest

from specvsreality_worker.config import WorkerSettings


@pytest.fixture
def worker_settings() -> WorkerSettings:
    return WorkerSettings()


@pytest.fixture(scope="session", autouse=True)
def _disable_opik_in_tests() -> None:
    """Avoid @opik.track HTTP side effects when the suite runs without Opik."""
    import opik

    opik.set_tracing_active(False)
    yield
    opik.reset_tracing_to_config_default()
