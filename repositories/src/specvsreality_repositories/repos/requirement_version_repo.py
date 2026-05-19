"""Requirement version row access."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.requirement_version import RequirementVersion


class RequirementVersionRepo:
    """Read/write access for the ``requirement_versions`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, requirement_version_id: int) -> RequirementVersion | None:
        return self._session.get(RequirementVersion, requirement_version_id)

    def insert(
        self,
        *,
        requirement_id: int,
        spec_version_id: int,
        content: str,
        content_hash: str,
        extraction_model: str,
        extraction_prompt: str,
        path_globs: list[str] | None = None,
    ) -> RequirementVersion:
        row = RequirementVersion(
            requirement_id=requirement_id,
            spec_version_id=spec_version_id,
            content=content,
            content_hash=content_hash,
            extraction_model=extraction_model,
            extraction_prompt=extraction_prompt,
            path_globs=list(path_globs or []),
        )
        self._session.add(row)
        self._session.flush()
        return row

    def exists(self, *, requirement_id: int, spec_version_id: int) -> bool:
        stmt = (
            select(RequirementVersion.id)
            .where(
                RequirementVersion.requirement_id == requirement_id,
                RequirementVersion.spec_version_id == spec_version_id,
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first() is not None

    def get_for_pair(
        self, *, requirement_id: int, spec_version_id: int
    ) -> RequirementVersion | None:
        stmt = (
            select(RequirementVersion)
            .where(
                RequirementVersion.requirement_id == requirement_id,
                RequirementVersion.spec_version_id == spec_version_id,
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def latest_for_requirement(
        self, *, requirement_id: int
    ) -> RequirementVersion | None:
        stmt = (
            select(RequirementVersion)
            .where(RequirementVersion.requirement_id == requirement_id)
            .order_by(
                desc(RequirementVersion.extracted_at),
                desc(RequirementVersion.id),
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def for_spec_version(
        self, *, spec_version_id: int
    ) -> list[RequirementVersion]:
        stmt = (
            select(RequirementVersion)
            .where(RequirementVersion.spec_version_id == spec_version_id)
            .order_by(RequirementVersion.requirement_id.asc(), RequirementVersion.id.asc())
        )
        return list(self._session.scalars(stmt).all())


def create_requirement_version_repo(session: Session) -> RequirementVersionRepo:
    return RequirementVersionRepo(session)
