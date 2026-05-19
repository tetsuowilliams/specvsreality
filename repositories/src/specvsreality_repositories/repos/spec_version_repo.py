"""Spec version row access."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ColumnElement, desc, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from specvsreality_repositories.models.spec_version import SpecVersion


def _eq_or_null(
    column: InstrumentedAttribute[str | None], value: str | None
) -> ColumnElement[bool]:
    """``column = value`` for non-None, ``column IS NULL`` for None.

    ``Column.is_(...)`` only emits valid SQL for ``None``/``True``/``False``
    so we cannot reuse it as a "null-aware equality" -- this helper picks the
    right operator at call time.
    """
    if value is None:
        return column.is_(None)
    return column == value


class SpecVersionRepo:
    """Read/write access for the ``spec_versions`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, spec_version_id: int) -> SpecVersion | None:
        return self._session.get(SpecVersion, spec_version_id)

    def find_by_triplet(
        self,
        *,
        spec_id: int,
        spec_blob_sha: str,
        plan_blob_sha: str | None,
        tasks_blob_sha: str | None,
    ) -> SpecVersion | None:
        """Look up an existing version by its ``(spec, plan, tasks)`` blob trio.

        ``plan_blob_sha`` / ``tasks_blob_sha`` may be ``None``; null slots are
        compared with ``IS NULL`` so SQL's three-valued logic doesn't silently
        miss matches.
        """
        stmt = (
            select(SpecVersion)
            .where(
                SpecVersion.spec_id == spec_id,
                SpecVersion.spec_blob_sha == spec_blob_sha,
                _eq_or_null(SpecVersion.plan_blob_sha, plan_blob_sha),
                _eq_or_null(SpecVersion.tasks_blob_sha, tasks_blob_sha),
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def insert(
        self,
        *,
        spec_id: int,
        spec_blob_sha: str,
        plan_blob_sha: str | None,
        tasks_blob_sha: str | None,
        first_seen_commit: str,
        first_seen_at: datetime,
    ) -> SpecVersion:
        row = SpecVersion(
            spec_id=spec_id,
            spec_blob_sha=spec_blob_sha,
            plan_blob_sha=plan_blob_sha,
            tasks_blob_sha=tasks_blob_sha,
            first_seen_commit=first_seen_commit,
            first_seen_at=first_seen_at,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def latest_for_spec(self, *, spec_id: int) -> SpecVersion | None:
        stmt = (
            select(SpecVersion)
            .where(SpecVersion.spec_id == spec_id)
            .order_by(desc(SpecVersion.first_seen_at), desc(SpecVersion.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()


def create_spec_version_repo(session: Session) -> SpecVersionRepo:
    return SpecVersionRepo(session)
