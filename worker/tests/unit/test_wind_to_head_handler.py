from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from git import Repo
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import WindToHeadMessage
from specvsreality_repositories.models import Base, GitRepo
from specvsreality_repositories.repos.scan_selection_repo import (
    ImplementationLinkedSpecRow,
    UnderImplementedSpecRow,
)
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core.scan_selection import ScanReason, ScanTarget
from specvsreality_worker.core.spec_detection import ArtifactType
from specvsreality_worker.git_adapter import ChangedPath, GitCommitPathInformation, PathChangeState
from specvsreality_worker.handlers.wind_to_head import WindToHeadHandler


def test_wind_to_head_advances_cursor_and_scans_selectively(tmp_path: Path) -> None:
    source_repo_path = tmp_path / "source"
    source_repo_path.mkdir()
    source_repo = Repo.init(str(source_repo_path))
    (source_repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    source_repo.index.add(["README.md"])
    source_repo.index.commit("init")
    (source_repo_path / "second.txt").write_text("more\n", encoding="utf-8")
    source_repo.index.add(["second.txt"])
    source_repo.index.commit("second")

    all_shas = [c.hexsha for c in reversed(list(source_repo.iter_commits()))]
    first_sha = all_shas[0]
    second_sha = all_shas[1]

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__])
    with Session(bind=engine) as session:
        row = GitRepo(
            name="source",
            url=str(source_repo_path),
            cursor_position=first_sha,
            location=str(source_repo_path),
        )
        session.add(row)
        session.commit()
        repo_id = row.id

    settings = WorkerSettings(database_url=db_url)
    spec_scanner = MagicMock()
    spec_scanner.scan_async = AsyncMock()
    handler = WindToHeadHandler(settings=settings, spec_scanner=spec_scanner)

    changes = GitCommitPathInformation(
        paths=[
            ChangedPath(
                path="specs/feature/spec.md",
                state=PathChangeState.NEW,
                artifact_type=ArtifactType.SPEC,
            )
        ]
    )
    commit_context = MagicMock()
    commit_context.commit_id = 99

    with (
        patch(
            "specvsreality_worker.handlers.wind_to_head.sync_commit_artifacts",
            return_value=(commit_context, changes),
        ),
        patch(
            "specvsreality_worker.handlers.wind_to_head.create_scan_selection_repo",
        ) as scan_repo_factory,
        patch(
            "specvsreality_worker.handlers.wind_to_head.record_scan_decisions",
        ) as record_logs,
    ):
        scan_repo = MagicMock()
        scan_repo.list_under_implemented_specs_at_commit.return_value = []
        scan_repo.list_specs_for_changed_artifacts_at_commit.return_value = []
        scan_repo_factory.return_value = scan_repo
        handler.handle(WindToHeadMessage(repo_id=str(repo_id)))

    with Session(bind=engine) as session:
        updated = session.get(GitRepo, repo_id)
        assert updated is not None
        assert updated.cursor_position == second_sha

    spec_scanner.scan_async.assert_awaited_once()
    await_kwargs = spec_scanner.scan_async.await_args.kwargs
    assert await_kwargs["spec_folder"] == "specs/feature"
    assert await_kwargs["extract_spec"] is True
    record_logs.assert_called_once()


def test_wind_to_head_rescans_under_implemented_and_linked_specs(tmp_path: Path) -> None:
    source_repo_path = tmp_path / "source"
    source_repo_path.mkdir()
    source_repo = Repo.init(str(source_repo_path))
    (source_repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    source_repo.index.add(["README.md"])
    source_repo.index.commit("init")
    (source_repo_path / "second.txt").write_text("more\n", encoding="utf-8")
    source_repo.index.add(["second.txt"])
    source_repo.index.commit("second")

    all_shas = [c.hexsha for c in reversed(list(source_repo.iter_commits()))]
    first_sha = all_shas[0]

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__])
    with Session(bind=engine) as session:
        row = GitRepo(
            name="source",
            url=str(source_repo_path),
            cursor_position=first_sha,
            location=str(source_repo_path),
        )
        session.add(row)
        session.commit()
        repo_id = row.id

    settings = WorkerSettings(database_url=db_url)
    spec_scanner = MagicMock()
    spec_scanner.scan_async = AsyncMock()
    handler = WindToHeadHandler(settings=settings, spec_scanner=spec_scanner)

    code_changes = GitCommitPathInformation(
        paths=[
            ChangedPath(
                path="src/app.py",
                state=PathChangeState.NEW,
                artifact_type=ArtifactType.CODE,
            )
        ]
    )
    first_commit = MagicMock()
    first_commit.commit_id = 101
    second_commit = MagicMock()
    second_commit.commit_id = 102

    with (
        patch(
            "specvsreality_worker.handlers.wind_to_head.sync_commit_artifacts",
            side_effect=[(first_commit, code_changes), (second_commit, code_changes)],
        ),
        patch(
            "specvsreality_worker.handlers.wind_to_head.create_scan_selection_repo",
        ) as scan_repo_factory,
        patch("specvsreality_worker.handlers.wind_to_head.record_scan_decisions"),
    ):
        scan_repo = MagicMock()
        scan_repo.list_under_implemented_specs_at_commit.side_effect = [
            [
                UnderImplementedSpecRow(
                    paper_id="specs/low",
                    tracked=5,
                    implemented=1,
                    coverage=20.0,
                )
            ],
            [],
        ]
        scan_repo.list_specs_for_changed_artifacts_at_commit.side_effect = [
            [
                ImplementationLinkedSpecRow(
                    paper_id="specs/linked",
                    filepaths=("src/app.py",),
                )
            ],
            [],
        ]
        scan_repo_factory.return_value = scan_repo
        handler.handle(WindToHeadMessage(repo_id=str(repo_id)))

    assert spec_scanner.scan_async.await_count == 2
    folders = [call.kwargs["spec_folder"] for call in spec_scanner.scan_async.await_args_list]
    assert folders == ["specs/linked", "specs/low"]


def test_wind_to_head_continues_when_scan_fails(tmp_path: Path) -> None:
    source_repo_path = tmp_path / "source"
    source_repo_path.mkdir()
    source_repo = Repo.init(str(source_repo_path))
    (source_repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    source_repo.index.add(["README.md"])
    source_repo.index.commit("init")
    (source_repo_path / "second.txt").write_text("more\n", encoding="utf-8")
    source_repo.index.add(["second.txt"])
    source_repo.index.commit("second")
    (source_repo_path / "third.txt").write_text("even more\n", encoding="utf-8")
    source_repo.index.add(["third.txt"])
    source_repo.index.commit("third")

    all_shas = [c.hexsha for c in reversed(list(source_repo.iter_commits()))]
    first_sha = all_shas[0]
    second_sha = all_shas[1]

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__])
    with Session(bind=engine) as session:
        row = GitRepo(
            name="source",
            url=str(source_repo_path),
            cursor_position=first_sha,
            location=str(source_repo_path),
        )
        session.add(row)
        session.commit()
        repo_id = row.id

    settings = WorkerSettings(database_url=db_url)
    spec_scanner = MagicMock()
    spec_scanner.scan_async = AsyncMock(
        side_effect=[None, RuntimeError("scan failed")],
    )
    handler = WindToHeadHandler(settings=settings, spec_scanner=spec_scanner)

    changes = GitCommitPathInformation(
        paths=[
            ChangedPath(
                path="specs/feature/spec.md",
                state=PathChangeState.NEW,
                artifact_type=ArtifactType.SPEC,
            )
        ]
    )
    first_commit = MagicMock()
    first_commit.commit_id = 101
    second_commit = MagicMock()
    second_commit.commit_id = 102

    with (
        patch(
            "specvsreality_worker.handlers.wind_to_head.sync_commit_artifacts",
            side_effect=[(first_commit, changes), (second_commit, changes)],
        ),
        patch(
            "specvsreality_worker.handlers.wind_to_head.create_scan_selection_repo",
        ) as scan_repo_factory,
        patch("specvsreality_worker.handlers.wind_to_head.record_scan_decisions"),
    ):
        scan_repo = MagicMock()
        scan_repo.list_under_implemented_specs_at_commit.return_value = []
        scan_repo.list_specs_for_changed_artifacts_at_commit.return_value = []
        scan_repo_factory.return_value = scan_repo

        handler.handle(WindToHeadMessage(repo_id=str(repo_id)))

    with Session(bind=engine) as session:
        updated = session.get(GitRepo, repo_id)
        assert updated is not None
        assert updated.cursor_position == all_shas[-1]
