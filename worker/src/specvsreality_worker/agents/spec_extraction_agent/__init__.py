"""Spec extraction agent interfaces and factory."""

from specvsreality_worker.agents.spec_extraction_agent.agent import (
    SpecExtractionAgent,
    create_spec_extraction_agent,
)
from specvsreality_worker.agents.spec_extraction_agent.models import (
    ExtractedSpec,
    ExtractedSpecItem,
)

__all__ = [
    "ExtractedSpec",
    "ExtractedSpecItem",
    "SpecExtractionAgent",
    "create_spec_extraction_agent",
]
