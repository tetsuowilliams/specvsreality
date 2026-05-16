"""Spec extraction agent interfaces and factory."""

from specvsreality_worker.agents.spec_extraction_agent.agent import (
    SpecExtractionAgent,
    create_spec_extraction_agent,
)
from specvsreality_worker.agents.spec_extraction_agent.models import (
    ParsedRequirement,
    SpecExtractionResult,
)

FunctionalRequirement = ParsedRequirement

__all__ = [
    "FunctionalRequirement",
    "SpecExtractionAgent",
    "SpecExtractionResult",
    "create_spec_extraction_agent",
]
