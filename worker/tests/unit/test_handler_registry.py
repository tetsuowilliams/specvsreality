"""Handler registry wiring."""

from __future__ import annotations

import pytest

from specvsreality_worker.handlers import HelloWorldHandler
from specvsreality_worker.messaging.handler_registry import HandlerRegistry


def test_registry_resolves_handler() -> None:
    h = HelloWorldHandler()
    registry = HandlerRegistry([h])
    assert registry.require(h.message_type) is h


def test_registry_rejects_duplicate_message_type() -> None:
    with pytest.raises(ValueError, match="duplicate handler"):
        HandlerRegistry([HelloWorldHandler(), HelloWorldHandler()])
