"""Requirement row access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.requirement import Requirement


class RequirementRepo:
    """Read/write access for the ``requirements`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, requirement_id: int) -> Requirement | None:
        return self._session.get(Requirement, requirement_id)

    def get_by_external_id(
        self, *, spec_id: int, external_id: str
    ) -> Requirement | None:
        stmt = (
            select(Requirement)
            .where(
                Requirement.spec_id == spec_id,
                Requirement.external_id == external_id,
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_or_create(self, *, spec_id: int, external_id: str) -> Requirement:
        existing = self.get_by_external_id(
            spec_id=spec_id, external_id=external_id
        )
        if existing is not None:
            return existing
        row = Requirement(spec_id=spec_id, external_id=external_id)
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_spec(self, *, spec_id: int) -> list[Requirement]:
        stmt = (
            select(Requirement)
            .where(Requirement.spec_id == spec_id)
            .order_by(Requirement.external_id.asc(), Requirement.id.asc())
        )
        return list(self._session.scalars(stmt).all())


def create_requirement_repo(session: Session) -> RequirementRepo:
    return RequirementRepo(session)
