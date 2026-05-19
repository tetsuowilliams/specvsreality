"""Spec detection, version resolution, and requirement extraction."""

from specvsreality_worker.spec.requirement_extractor import RequirementExtractor
from specvsreality_worker.spec.requirement_version_writer import (
    RequirementVersionWriter,
)
from specvsreality_worker.spec.spec_detector import SpecDetector
from specvsreality_worker.spec.spec_version_resolver import SpecVersionResolver

__all__ = [
    "RequirementExtractor",
    "RequirementVersionWriter",
    "SpecDetector",
    "SpecVersionResolver",
]
