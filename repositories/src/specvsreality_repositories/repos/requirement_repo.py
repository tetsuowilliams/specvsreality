"""Repository access for requirements."""

from __future__ import annotations

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.requirement import Requirement
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.repos.enums import VersionStatus


class RequirementRepo:
    """Read/write access for requirement rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, requirement_id: int) -> Requirement | None:
        return self._session.get(Requirement, requirement_id)

    def get_by_spec_and_paper_id(self, *, spec_id: int, paper_id: str) -> Requirement | None:
        stmt = (
            select(Requirement)
            .where(Requirement.spec_id == spec_id, Requirement.paper_id == paper_id)
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def add(self, *, spec_id: int, paper_id: str) -> Requirement:
        row = Requirement(spec_id=spec_id, paper_id=paper_id)
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_spec(self, *, spec_id: int) -> list[Requirement]:
        stmt = (
            select(Requirement)
            .where(Requirement.spec_id == spec_id)
            .order_by(Requirement.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def list_latest_active_for_spec(self, *, spec_id: int) -> list[Requirement]:
        latest_versions = (
            select(
                RequirementVersion.requirement_id.label("requirement_id"),
                RequirementVersion.status.label("status"),
                func.row_number()
                .over(
                    partition_by=RequirementVersion.requirement_id,
                    order_by=(
                        desc(RequirementVersion.commit_datetime),
                        desc(RequirementVersion.id),
                    ),
                )
                .label("rn"),
            )
            .subquery()
        )
        stmt = (
            select(Requirement)
            .join(latest_versions, latest_versions.c.requirement_id == Requirement.id)
            .where(
                Requirement.spec_id == spec_id,
                latest_versions.c.rn == 1,
                latest_versions.c.status == VersionStatus.ACTIVE.value,
            )
            .order_by(Requirement.id.asc())
        )
        return list(self._session.execute(stmt).scalars().all())


def create_requirement_repo(session: Session) -> RequirementRepo:
    return RequirementRepo(session)
