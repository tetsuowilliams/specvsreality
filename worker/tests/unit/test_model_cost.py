"""Tests for model token cost calculation."""

from __future__ import annotations

from decimal import Decimal

from specvsreality_worker.model_token_cost import ModelTokenCost, calculate_cost_usd


def test_calculate_cost_usd_with_separate_rates() -> None:
    costs = {
        "openai:gpt-4o-mini": ModelTokenCost(input_per_million=0.15, output_per_million=0.60),
    }
    result = calculate_cost_usd(
        costs,
        model="openai:gpt-4o-mini",
        input_tokens=1_000_000,
        output_tokens=500_000,
    )
    assert result == Decimal("0.45")


def test_calculate_cost_usd_unknown_model_returns_zero() -> None:
    result = calculate_cost_usd(
        {},
        model="unknown:model",
        input_tokens=1000,
        output_tokens=1000,
    )
    assert result == Decimal("0")
