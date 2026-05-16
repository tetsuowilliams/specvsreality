"""Repository access for spec versions."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.spec_version import SpecVersion


class SpecVersionRepo:
    """Read/write access for spec_version rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, version_id: int) -> SpecVersion | None:
        return self._session.get(SpecVersion, version_id)

    def list_for_spec_ordered(self, *, spec_id: int) -> list[SpecVersion]:
        stmt = (
            select(SpecVersion)
            .where(SpecVersion.spec_id == spec_id)
            .order_by(SpecVersion.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def add(
        self,
        *,
        spec_id: int,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
    ) -> SpecVersion:
        row = SpecVersion(spec_id=spec_id, spec_md=spec_md, tasks_md=tasks_md, plan_md=plan_md)
        self._session.add(row)
        self._session.flush()
        return row


def create_spec_version_repo(session: Session) -> SpecVersionRepo:
    return SpecVersionRepo(session)
