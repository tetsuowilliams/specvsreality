"""Repository access for specs."""

from __future__ import annotations

from pathlib import PurePosixPath

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from specvsreality_repositories.models.spec import Spec


def normalize_spec_folder(folder: str) -> str:
    """Canonical repo-relative spec directory path used as ``paper_id``."""
    return folder.replace("\\", "/").strip("/")


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

    def get_or_create_for_folder(self, *, folder: str, repo_id: int) -> tuple[Spec, bool]:
        """Resolve a spec row by normalized folder path, upserting when needed."""
        paper_id = normalize_spec_folder(folder)
        existing = self.get_by_paper_id(paper_id=paper_id, repo_id=repo_id)
        if existing is not None:
            return existing, False

        basename = PurePosixPath(paper_id).name
        if basename and basename != paper_id:
            legacy = self.get_by_paper_id(paper_id=basename, repo_id=repo_id)
            if legacy is not None:
                legacy.paper_id = paper_id
                self._session.flush()
                return legacy, False

        inserted = self._session.execute(
            pg_insert(Spec)
            .values(paper_id=paper_id, repo_id=repo_id)
            .on_conflict_do_nothing(constraint="uq_spec_repo_paper_id")
            .returning(Spec.id)
        ).first()
        if inserted is not None:
            row = self.get_by_id(int(inserted[0]))
            if row is None:
                raise RuntimeError(f"spec insert succeeded but row missing: id={inserted[0]}")
            return row, True

        existing = self.get_by_paper_id(paper_id=paper_id, repo_id=repo_id)
        if existing is None:
            raise RuntimeError(f"failed to get_or_create spec for folder={paper_id!r}")
        return existing, False


def create_spec_repo(session: Session) -> SpecRepo:
    return SpecRepo(session)
