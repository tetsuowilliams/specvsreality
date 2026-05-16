"""Repository access for specs."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.spec import Spec


class SpecRepo:
    """Read/write access for spec rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, spec_id: int) -> Spec | None:
        return self._session.get(Spec, spec_id)

    def list_for_repo(self, *, repo_id: int) -> list[Spec]:
        stmt = (
            select(Spec)
            .where(Spec.repo_id == repo_id)
            .order_by(Spec.paper_id.asc(), Spec.id.asc())
        )
        return list(self._session.scalars(stmt).all())

    def get_by_paper_id(self, *, paper_id: str, repo_id: int) -> Spec | None:
        """Return the spec for this repository and paper (spec directory identity)."""
        stmt = select(Spec).where(Spec.paper_id == paper_id, Spec.repo_id == repo_id).limit(1)
        return self._session.execute(stmt).scalars().first()

    def add(self, *, paper_id: str, repo_id: int) -> Spec:
        row = Spec(paper_id=paper_id, repo_id=repo_id)
        self._session.add(row)
        self._session.flush()
        return row


def create_spec_repo(session: Session) -> SpecRepo:
    return SpecRepo(session)
