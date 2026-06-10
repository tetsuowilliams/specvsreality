from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_repositories.models import Base, Commit, GitRepo
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.spec_scanner import SpecScanner


def test_spec_scanner_runs_extraction_and_downstream(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__, Commit.__table__])

    committed_at = datetime(2024, 1, 1, tzinfo=UTC)
    with Session(bind=engine) as session:
        repo = GitRepo(
            name="repo",
            url="https://example.test/repo.git",
            cursor_position="abc",
            location=str(tmp_path / "clone"),
        )
        session.add(repo)
        session.flush()
        commit = Commit(
            repo_id=repo.id,
            commit_sha="deadbeef" * 5,
            commit_message="msg",
            committed_at=committed_at,
        )
        session.add(commit)
        session.commit()
        repo_id = repo.id
        commit_id = commit.id

    settings = WorkerSettings(database_url=db_url)
    work = SimpleNamespace(spec_version=SimpleNamespace(id=501))
    resolved = [SimpleNamespace()]
    commit_ctx = CommitContext(
        repo_id=repo_id,
        commit_id=commit_id,
        commit_sha="deadbeef" * 5,
        commit_datetime=committed_at,
        commit_message="msg",
    )

    with (
        patch("specvsreality_worker.core.spec_scanner.create_spec_extraction_agent"),
        patch("specvsreality_worker.core.spec_scanner.create_artifact_candidate_agent"),
        patch("specvsreality_worker.core.spec_scanner.create_implements_agent"),
    ):
        spec_merge = MagicMock()
        spec_merge.merge_spec_folder_async = AsyncMock(return_value=work)
        candidate_discovery = MagicMock()
        candidate_discovery.discover_async = AsyncMock(return_value=resolved)
        implements_evaluation = MagicMock()
        implements_evaluation.evaluate_async = AsyncMock()

        with (
            patch("specvsreality_worker.core.spec_scanner.SpecMerge", return_value=spec_merge),
            patch(
                "specvsreality_worker.core.spec_scanner.CandidateDiscovery",
                return_value=candidate_discovery,
            ),
            patch(
                "specvsreality_worker.core.spec_scanner.ImplementsEvaluation",
                return_value=implements_evaluation,
            ),
        ):
            with Session(bind=engine) as session:
                scanner = SpecScanner(
                    settings=settings,
                    session=session,
                    git_adapter=MagicMock(),
                )
                asyncio.run(
                    scanner.scan_async(
                        commit=commit_ctx,
                        spec_folder="specs/feature",
                        extract_spec=True,
                    )
                )

    spec_merge.merge_spec_folder_async.assert_awaited_once()
    spec_merge.load_spec_work_for_evaluation.assert_not_called()
    candidate_discovery.discover_async.assert_awaited_once()
    implements_evaluation.evaluate_async.assert_awaited_once()


def test_spec_scanner_loads_from_db_when_extract_spec_false(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__, Commit.__table__])

    committed_at = datetime(2024, 1, 1, tzinfo=UTC)
    with Session(bind=engine) as session:
        repo = GitRepo(
            name="repo",
            url="https://example.test/repo.git",
            cursor_position="abc",
            location=str(tmp_path / "clone"),
        )
        session.add(repo)
        session.flush()
        commit = Commit(
            repo_id=repo.id,
            commit_sha="deadbeef" * 5,
            commit_message="msg",
            committed_at=committed_at,
        )
        session.add(commit)
        session.commit()
        repo_id = repo.id
        commit_id = commit.id

    settings = WorkerSettings(database_url=db_url)
    work = SimpleNamespace(spec_version=SimpleNamespace(id=501))
    commit_ctx = CommitContext(
        repo_id=repo_id,
        commit_id=commit_id,
        commit_sha="deadbeef" * 5,
        commit_datetime=committed_at,
        commit_message="msg",
    )

    with (
        patch("specvsreality_worker.core.spec_scanner.create_spec_extraction_agent"),
        patch("specvsreality_worker.core.spec_scanner.create_artifact_candidate_agent"),
        patch("specvsreality_worker.core.spec_scanner.create_implements_agent"),
    ):
        spec_merge = MagicMock()
        spec_merge.load_spec_work_for_evaluation.return_value = work
        candidate_discovery = MagicMock()
        candidate_discovery.discover_async = AsyncMock(return_value=[])
        implements_evaluation = MagicMock()
        implements_evaluation.evaluate_async = AsyncMock()

        with (
            patch("specvsreality_worker.core.spec_scanner.SpecMerge", return_value=spec_merge),
            patch(
                "specvsreality_worker.core.spec_scanner.CandidateDiscovery",
                return_value=candidate_discovery,
            ),
            patch(
                "specvsreality_worker.core.spec_scanner.ImplementsEvaluation",
                return_value=implements_evaluation,
            ),
        ):
            with Session(bind=engine) as session:
                scanner = SpecScanner(
                    settings=settings,
                    session=session,
                    git_adapter=MagicMock(),
                )
                asyncio.run(
                    scanner.scan_async(
                        commit=commit_ctx,
                        spec_folder="specs/feature",
                        extract_spec=False,
                    )
                )

    spec_merge.merge_spec_folder_async.assert_not_called()
    spec_merge.load_spec_work_for_evaluation.assert_called_once()
    implements_evaluation.evaluate_async.assert_awaited_once()
