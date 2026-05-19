"""Implementation claim row access (append-only judgments)."""

from __future__ import annotations

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from specvsreality_repositories.models.commit_file import CommitFile
from specvsreality_repositories.models.implementation_claim import ImplementationClaim


class ImplementationClaimRepo:
    """Read/write access for ``implementation_claims``.

    Rows are append-only: never updated, never deleted. "Current" verdicts are
    derived as the most recent ``evaluated_at`` per ``(requirement_version_id,
    blob_sha)`` pair.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def has_claim(
        self,
        *,
        requirement_version_id: int,
        blob_sha: str,
        model_version: str,
        prompt_version: str,
    ) -> bool:
        stmt = (
            select(ImplementationClaim.id)
            .where(
                ImplementationClaim.requirement_version_id == requirement_version_id,
                ImplementationClaim.blob_sha == blob_sha,
                ImplementationClaim.model_version == model_version,
                ImplementationClaim.prompt_version == prompt_version,
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first() is not None

    def insert(
        self,
        *,
        requirement_version_id: int,
        blob_sha: str,
        verdict: str,
        confidence: float | None,
        model_version: str,
        prompt_version: str,
        reasoning: str | None,
    ) -> ImplementationClaim:
        row = ImplementationClaim(
            requirement_version_id=requirement_version_id,
            blob_sha=blob_sha,
            verdict=verdict,
            confidence=confidence,
            model_version=model_version,
            prompt_version=prompt_version,
            reasoning=reasoning,
        )
        self._session.add(row)
        self._session.flush()
        return row

    def latest_for_pair(
        self, *, requirement_version_id: int, blob_sha: str
    ) -> ImplementationClaim | None:
        stmt = (
            select(ImplementationClaim)
            .where(
                ImplementationClaim.requirement_version_id == requirement_version_id,
                ImplementationClaim.blob_sha == blob_sha,
            )
            .order_by(
                desc(ImplementationClaim.evaluated_at),
                desc(ImplementationClaim.id),
            )
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def current_for_commit(
        self, *, commit_sha: str, requirement_version_id: int
    ) -> list[ImplementationClaim]:
        """Latest claim per blob present at ``commit_sha`` for one requirement version."""
        latest_subq = (
            select(
                ImplementationClaim.id,
                ImplementationClaim.blob_sha,
            )
            .where(
                ImplementationClaim.requirement_version_id == requirement_version_id,
            )
            .order_by(
                ImplementationClaim.blob_sha.asc(),
                desc(ImplementationClaim.evaluated_at),
                desc(ImplementationClaim.id),
            )
            .distinct(ImplementationClaim.blob_sha)
            .subquery()
        )

        stmt = (
            select(ImplementationClaim)
            .join(latest_subq, latest_subq.c.id == ImplementationClaim.id)
            .join(CommitFile, CommitFile.blob_sha == ImplementationClaim.blob_sha)
            .where(CommitFile.commit_sha == commit_sha)
            .order_by(ImplementationClaim.id.asc())
        )
        return list(self._session.scalars(stmt).unique().all())


def create_implementation_claim_repo(session: Session) -> ImplementationClaimRepo:
    return ImplementationClaimRepo(session)
