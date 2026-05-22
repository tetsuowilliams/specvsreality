"""Repository access for implementation evaluations at commits."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.implementation_at_commit import ImplementationAtCommit


class ImplementationAtCommitRepo:
    """Read/write access for ``implementation_at_commit`` rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, row_id: int) -> ImplementationAtCommit | None:
        return self._session.get(ImplementationAtCommit, row_id)

    def get_for_requirement_version_at_commit(
        self,
        *,
        requirement_version_id: int,
        evaluation_commit_sha: str,
    ) -> ImplementationAtCommit | None:
        stmt = select(ImplementationAtCommit).where(
            ImplementationAtCommit.requirement_version_id == requirement_version_id,
            ImplementationAtCommit.evaluation_commit_sha == evaluation_commit_sha,
        )
        return self._session.scalars(stmt).first()

    def list_for_requirement_versions(
        self,
        *,
        requirement_version_ids: list[int],
    ) -> list[ImplementationAtCommit]:
        if not requirement_version_ids:
            return []
        stmt = (
            select(ImplementationAtCommit)
            .where(ImplementationAtCommit.requirement_version_id.in_(requirement_version_ids))
            .order_by(
                ImplementationAtCommit.requirement_version_id.asc(),
                ImplementationAtCommit.evaluation_commit_sha.asc(),
            )
        )
        return list(self._session.scalars(stmt).all())

    def get_latest_for_requirement_version(
        self,
        *,
        requirement_version_id: int,
    ) -> ImplementationAtCommit | None:
        stmt = (
            select(ImplementationAtCommit)
            .where(ImplementationAtCommit.requirement_version_id == requirement_version_id)
            .order_by(desc(ImplementationAtCommit.evaluation_commit_sha), desc(ImplementationAtCommit.id))
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def upsert_evaluation(
        self,
        *,
        requirement_version_id: int,
        evaluation_commit_sha: str,
        implemented: bool,
        summary: str,
        gaps: list[str],
        confidence: str | None = None,
    ) -> ImplementationAtCommit:
        row = self.get_for_requirement_version_at_commit(
            requirement_version_id=requirement_version_id,
            evaluation_commit_sha=evaluation_commit_sha,
        )
        if row is None:
            row = ImplementationAtCommit(
                requirement_version_id=requirement_version_id,
                evaluation_commit_sha=evaluation_commit_sha,
                implemented=implemented,
                summary=summary,
                gaps=gaps,
                confidence=confidence,
            )
            self._session.add(row)
        else:
            row.implemented = implemented
            row.summary = summary
            row.gaps = gaps
            row.confidence = confidence

        self._session.flush()
        return row


def create_implementation_at_commit_repo(session: Session) -> ImplementationAtCommitRepo:
    return ImplementationAtCommitRepo(session)
