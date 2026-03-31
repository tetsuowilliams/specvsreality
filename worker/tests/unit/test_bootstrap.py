"""Composition root guards."""

from __future__ import annotations

import pytest

from specvsreality_worker.bootstrap import build_handler_registry


def test_bootstrap_requires_handler_for_each_known_message_type() -> None:
    with pytest.raises(RuntimeError, match="handlers missing"):
        build_handler_registry(())
