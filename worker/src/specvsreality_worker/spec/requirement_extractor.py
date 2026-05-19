"""Run the spec extraction agent over a SpecVersion and persist results."""

from __future__ import annotations

import logging

from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_worker.agents.spec_extraction_agent import SpecExtractionAgent
from specvsreality_worker.domain import ExtractedRequirement
from specvsreality_worker.ingestion_config import ExtractionConfig
from specvsreality_worker.spec.requirement_version_writer import (
    RequirementVersionWriter,
)
from specvsreality_worker.support import BlobReader

logger = logging.getLogger(__name__)


class RequirementExtractor:
    """Extract requirements from one ``SpecVersion`` and persist them.

    Reads the three blobs that define the version, asks the LLM agent to
    return structured requirements, and delegates persistence to
    :class:`RequirementVersionWriter` (which handles dedup).
    """

    def __init__(
        self,
        *,
        spec_extraction_agent: SpecExtractionAgent,
        blob_reader: BlobReader,
        requirement_version_writer: RequirementVersionWriter,
        config: ExtractionConfig,
    ) -> None:
        self._agent = spec_extraction_agent
        self._blob_reader = blob_reader
        self._writer = requirement_version_writer
        self._config = config

    def extract(self, *, spec_version: SpecVersion) -> list[RequirementVersion]:
        spec_text = self._blob_reader.read_text(spec_version.spec_blob_sha)
        plan_text = self._read_optional(spec_version.plan_blob_sha)
        tasks_text = self._read_optional(spec_version.tasks_blob_sha)

        result = self._agent.extract_spec(
            spec_md=spec_text,
            tasks_md=tasks_text,
            plan_md=plan_text,
        )

        out: list[RequirementVersion] = []
        for parsed in result.functional_requirements:
            if not parsed.id:
                logger.warning(
                    "skipping requirement with empty id under spec_version=%s",
                    spec_version.id,
                )
                continue
            extracted = ExtractedRequirement(
                external_id=parsed.id,
                content=parsed.text,
                path_globs=tuple(parsed.path_globs),
            )
            out.append(
                self._writer.write(
                    spec_version=spec_version,
                    extracted=extracted,
                    extraction_model=self._config.extraction_model,
                    extraction_prompt=self._config.extraction_prompt,
                )
            )
        return out

    def _read_optional(self, blob_sha: str | None) -> str | None:
        """Pass through ``None`` for absent ``plan.md`` / ``tasks.md`` blobs."""
        if blob_sha is None:
            return None
        return self._blob_reader.read_text(blob_sha)
