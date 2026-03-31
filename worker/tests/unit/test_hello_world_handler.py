"""HelloWorld handler behavior."""

from __future__ import annotations

import logging

import pytest

from specvsreality_messages import HelloWorldMessage
from specvsreality_worker.handlers import HelloWorldHandler


def test_handler_logs_name(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    handler = HelloWorldHandler()
    handler.handle(HelloWorldMessage(name="Ada"))
    assert any("Ada" in r.getMessage() for r in caplog.records)


def test_handler_rejects_wrong_model_type() -> None:
    from pydantic import BaseModel

    class Other(BaseModel):
        x: int

    handler = HelloWorldHandler()
    with pytest.raises(TypeError, match="HelloWorldMessage"):
        handler.handle(Other(x=1))
