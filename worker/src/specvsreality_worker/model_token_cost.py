"""Compute LLM run cost from configured per-model token rates."""

from __future__ import annotations

import json
import logging
from decimal import Decimal

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class ModelTokenCost(BaseModel):
    """USD cost per million tokens for a model."""

    input_per_million: float = Field(ge=0)
    output_per_million: float = Field(ge=0)


def parse_model_token_costs(raw: object) -> dict[str, ModelTokenCost]:
    if raw is None:
        return {}
    if isinstance(raw, str):
        if not raw.strip():
            return {}
        data = json.loads(raw)
    else:
        data = raw
    if not isinstance(data, dict):
        return {}
    return {model: ModelTokenCost.model_validate(rates) for model, rates in data.items()}


def calculate_cost_usd(
    model_token_costs: dict[str, ModelTokenCost],
    *,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> Decimal:
    rates = model_token_costs.get(model)
    if rates is None:
        logger.warning("no token cost configured for model=%s; recording zero cost", model)
        return Decimal("0")
    input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * Decimal(str(rates.input_per_million))
    output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * Decimal(str(rates.output_per_million))
    return input_cost + output_cost
