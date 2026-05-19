"""Configuration objects for the ingestion pipeline.

These are small frozen dataclasses passed to the units that need them.
Distinct from ``specvsreality_worker.config`` which holds RabbitMQ settings.
"""

from specvsreality_worker.ingestion_config.evaluation_config import EvaluationConfig
from specvsreality_worker.ingestion_config.extraction_config import ExtractionConfig
from specvsreality_worker.ingestion_config.spec_pattern_config import SpecPatternConfig

__all__ = [
    "EvaluationConfig",
    "ExtractionConfig",
    "SpecPatternConfig",
]
