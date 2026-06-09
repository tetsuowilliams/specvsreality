from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import SpecScanMessage
from specvsreality_repositories.models import Base, Commit, GitRepo
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.handlers.spec_scan import SpecScanHandler


def test_spec_scan_runs_extraction_and_downstream(tmp_path) -> None:
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
    handler = SpecScanHandler(settings=settings)

    work = SimpleNamespace(spec_version=SimpleNamespace(id=501))
    resolved = [SimpleNamespace()]

    with (
        patch("specvsreality_worker.handlers.spec_scan.GitAdapter") as git_adapter_cls,
        patch("specvsreality_worker.handlers.spec_scan.create_spec_extraction_agent"),
        patch("specvsreality_worker.handlers.spec_scan.create_artifact_candidate_agent"),
        patch("specvsreality_worker.handlers.spec_scan.create_implements_agent"),
    ):
        spec_merge = MagicMock()
        spec_merge.merge_spec_folder.return_value = work
        candidate_discovery = MagicMock()
        candidate_discovery.discover.return_value = resolved
        implements_evaluation = MagicMock()

        with (
            patch("specvsreality_worker.handlers.spec_scan.SpecMerge", return_value=spec_merge),
            patch(
                "specvsreality_worker.handlers.spec_scan.CandidateDiscovery",
                return_value=candidate_discovery,
            ),
            patch(
                "specvsreality_worker.handlers.spec_scan.ImplementsEvaluation",
                return_value=implements_evaluation,
            ),
        ):
            git_adapter_cls.return_value = MagicMock()
            handler.handle(
                SpecScanMessage(
                    repo_id=str(repo_id),
                    commit_id=commit_id,
                    spec_folder="specs/feature",
                )
            )

    spec_merge.merge_spec_folder.assert_called_once()
    candidate_discovery.discover.assert_called_once_with(
        commit=spec_merge.merge_spec_folder.call_args.kwargs["commit"],
        work=work,
        metrics=spec_merge.merge_spec_folder.call_args.kwargs["metrics"],
    )
    implements_evaluation.evaluate.assert_called_once()


def test_spec_scan_skips_when_no_spec_md(tmp_path) -> None:
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__, Commit.__table__])

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
            committed_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        session.add(commit)
        session.commit()
        repo_id = repo.id
        commit_id = commit.id

    settings = WorkerSettings(database_url=db_url)
    handler = SpecScanHandler(settings=settings)

    with (
        patch("specvsreality_worker.handlers.spec_scan.GitAdapter"),
        patch("specvsreality_worker.handlers.spec_scan.create_spec_extraction_agent"),
        patch("specvsreality_worker.handlers.spec_scan.create_artifact_candidate_agent"),
        patch("specvsreality_worker.handlers.spec_scan.create_implements_agent"),
        patch("specvsreality_worker.handlers.spec_scan.SpecMerge") as spec_merge_cls,
        patch("specvsreality_worker.handlers.spec_scan.CandidateDiscovery") as discovery_cls,
        patch("specvsreality_worker.handlers.spec_scan.ImplementsEvaluation") as eval_cls,
    ):
        spec_merge = MagicMock()
        spec_merge.merge_spec_folder.return_value = None
        spec_merge_cls.return_value = spec_merge

        handler.handle(
            SpecScanMessage(
                repo_id=str(repo_id),
                commit_id=commit_id,
                spec_folder="specs/feature",
            )
        )

    discovery_cls.return_value.discover.assert_not_called()
    eval_cls.return_value.evaluate.assert_not_called()
