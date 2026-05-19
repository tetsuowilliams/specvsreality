"""Domain dataclasses for the temporal ingestion pipeline.

These are plain dataclasses used by orchestration / pipeline classes.
ORM rows from ``specvsreality_repositories`` carry persisted state; these
types carry transient values flowing between pipeline stages.
"""

from specvsreality_worker.domain.commit_record import CommitRecord, ParentRef
from specvsreality_worker.domain.detected_spec import DetectedSpec
from specvsreality_worker.domain.extracted_requirement import ExtractedRequirement
from specvsreality_worker.domain.spec_file_triplet import SpecFileTriplet
from specvsreality_worker.domain.spec_version_resolution import SpecVersionResolution
from specvsreality_worker.domain.tree_entry import TreeEntry

__all__ = [
    "CommitRecord",
    "DetectedSpec",
    "ExtractedRequirement",
    "ParentRef",
    "SpecFileTriplet",
    "SpecVersionResolution",
    "TreeEntry",
]
