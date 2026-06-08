"""Repository access for implementation evaluations at commits."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.implementation_at_commit import ImplementationAtCommit


class ImplementationAtCommitRepo:
    """Read/write access for ``implementation_at_commit`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, row_id: int) -> ImplementationAtCommit | None:
        return self._session.get(ImplementationAtCommit, row_id)

    def get_for_spec_item_at_commit(
        self,
        *,
        spec_item_id: int,
        commit_id: int,
    ) -> ImplementationAtCommit | None:
        stmt = select(ImplementationAtCommit).where(
            ImplementationAtCommit.spec_item_id == spec_item_id,
            ImplementationAtCommit.commit_id == commit_id,
        )
        return self._session.scalars(stmt).first()

    def list_for_spec_items(
        self,
        *,
        spec_item_ids: Sequence[int],
    ) -> list[ImplementationAtCommit]:
        if not spec_item_ids:
            return []
        stmt = (
            select(ImplementationAtCommit)
            .where(ImplementationAtCommit.spec_item_id.in_(spec_item_ids))
            .order_by(
                ImplementationAtCommit.spec_item_id.asc(),
                ImplementationAtCommit.commit_id.asc(),
            )
        )
        return list(self._session.scalars(stmt).all())

    def get_latest_for_spec_item(
        self,
        *,
        spec_item_id: int,
    ) -> ImplementationAtCommit | None:
        stmt = (
            select(ImplementationAtCommit)
            .where(ImplementationAtCommit.spec_item_id == spec_item_id)
            .order_by(desc(ImplementationAtCommit.commit_id), desc(ImplementationAtCommit.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def upsert_evaluation(
        self,
        *,
        spec_item_id: int,
        commit_id: int,
        implemented: bool,
        summary: str,
        gaps: Sequence[str],
        confidence: float | None = None,
    ) -> ImplementationAtCommit:
        row = self.get_for_spec_item_at_commit(
            spec_item_id=spec_item_id,
            commit_id=commit_id,
        )
        if row is None:
            row = ImplementationAtCommit(
                spec_item_id=spec_item_id,
                commit_id=commit_id,
                implemented=implemented,
                summary=summary,
                gaps=list(gaps),
                confidence=confidence,
            )
            self._session.add(row)
        else:
            row.implemented = implemented
            row.summary = summary
            row.gaps = list(gaps)
            row.confidence = confidence

        self._session.flush()
        return row


def create_implementation_at_commit_repo(session: Session) -> ImplementationAtCommitRepo:
    return ImplementationAtCommitRepo(session)
