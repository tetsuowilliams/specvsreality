"""Repository access for spec versions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos.enums import VersionStatus


class SpecVersionRepo:
    """Read/write access for spec_version rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, version_id: int) -> SpecVersion | None:
        return self._session.get(SpecVersion, version_id)

    def get_for_spec_at_commit(self, *, spec_id: int, commit_sha: str) -> SpecVersion | None:
        stmt = (
            select(SpecVersion)
            .where(SpecVersion.spec_id == spec_id, SpecVersion.commit_sha == commit_sha)
            .order_by(desc(SpecVersion.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

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
        commit_sha: str,
        created_at: datetime,
        committed_at: datetime | None,
        status: VersionStatus,
    ) -> SpecVersion:
        row = SpecVersion(
            spec_id=spec_id,
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
            commit_sha=commit_sha,
            created_at=created_at,
            committed_at=committed_at,
            status=status.value if isinstance(status, VersionStatus) else status,
        )
        self._session.add(row)
        self._session.flush()
        return row


def create_spec_version_repo(session: Session) -> SpecVersionRepo:
    return SpecVersionRepo(session)
