"""Spec row access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.spec import Spec


class SpecRepo:
    """Read/write access for the ``specs`` table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, spec_id: int) -> Spec | None:
        return self._session.get(Spec, spec_id)

    def get_by_name(self, *, repository_id: int, name: str) -> Spec | None:
        stmt = (
            select(Spec)
            .where(Spec.repository_id == repository_id, Spec.name == name)
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def get_or_create(
        self,
        *,
        repository_id: int,
        name: str,
        spec_path: str,
        plan_path: str,
        tasks_path: str,
    ) -> Spec:
        """Return the spec for ``name``, creating it or refreshing paths if moved.

        Identity is ``(repository_id, name)`` (the spec-kit folder name). When the
        same logical spec is relocated (e.g. ``test_speckit/specs/001/`` →
        ``specs/001/``), callers pass the paths from the current tree and we
        update the row so :class:`SpecVersionResolver` can resolve blobs at each
        commit.
        """
        existing = self.get_by_name(repository_id=repository_id, name=name)
        if existing is not None:
            if (
                existing.spec_path != spec_path
                or existing.plan_path != plan_path
                or existing.tasks_path != tasks_path
            ):
                existing.spec_path = spec_path
                existing.plan_path = plan_path
                existing.tasks_path = tasks_path
                self._session.flush()
            return existing
        row = Spec(
            repository_id=repository_id,
            name=name,
            spec_path=spec_path,
            plan_path=plan_path,
            tasks_path=tasks_path,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def list_for_repo(self, *, repository_id: int) -> list[Spec]:
        stmt = (
            select(Spec)
            .where(Spec.repository_id == repository_id)
            .order_by(Spec.name.asc(), Spec.id.asc())
        )
        return list(self._session.scalars(stmt).all())


def create_spec_repo(session: Session) -> SpecRepo:
    return SpecRepo(session)
