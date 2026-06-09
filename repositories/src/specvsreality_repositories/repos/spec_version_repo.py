"""Repository access for spec versions."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos.enums import VersionStatus


class SpecVersionRepo:
    """Read/write access for spec_version rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, version_id: int) -> SpecVersion | None:
        return self._session.get(SpecVersion, version_id)

    def get_for_spec_at_commit(self, *, spec_id: int, commit_id: int) -> SpecVersion | None:
        stmt = (
            select(SpecVersion)
            .where(SpecVersion.spec_id == spec_id, SpecVersion.commit_id == commit_id)
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
        commit_id: int,
        title: str | None,
        summary: str | None,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        created_at: datetime,
        status: VersionStatus,
    ) -> SpecVersion:
        row = SpecVersion(
            spec_id=spec_id,
            commit_id=commit_id,
            title=title,
            summary=summary,
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
            created_at=created_at,
            status=status.value if isinstance(status, VersionStatus) else status,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def get_or_create(
        self,
        *,
        spec_id: int,
        commit_id: int,
        title: str | None,
        summary: str | None,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        created_at: datetime,
        status: VersionStatus,
    ) -> tuple[SpecVersion, bool]:
        existing = self.get_for_spec_at_commit(spec_id=spec_id, commit_id=commit_id)
        if existing is not None:
            return existing, False

        status_value = status.value if isinstance(status, VersionStatus) else status
        inserted = self._session.execute(
            pg_insert(SpecVersion)
            .values(
                spec_id=spec_id,
                commit_id=commit_id,
                title=title,
                summary=summary,
                spec_md=spec_md,
                tasks_md=tasks_md,
                plan_md=plan_md,
                created_at=created_at,
                status=status_value,
            )
            .on_conflict_do_nothing(constraint="uq_spec_version_spec_commit")
            .returning(SpecVersion.id)
        ).first()
        if inserted is not None:
            row = self.get_by_id(int(inserted[0]))
            if row is None:
                raise RuntimeError(f"spec_version insert succeeded but row missing: id={inserted[0]}")
            return row, True

        existing = self.get_for_spec_at_commit(spec_id=spec_id, commit_id=commit_id)
        if existing is None:
            raise RuntimeError(
                f"failed to get_or_create spec_version spec_id={spec_id} commit_id={commit_id}"
            )
        return existing, False


def create_spec_version_repo(session: Session) -> SpecVersionRepo:
    return SpecVersionRepo(session)
