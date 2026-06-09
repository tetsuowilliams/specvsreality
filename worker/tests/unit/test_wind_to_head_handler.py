from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from git import Repo
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import SpecScanMessage, WindToHeadMessage
from specvsreality_repositories.models import Base, GitRepo
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core.spec_detection import ArtifactType
from specvsreality_worker.git_adapter import ChangedPath, GitCommitPathInformation, PathChangeState
from specvsreality_worker.handlers.wind_to_head import WindToHeadHandler


class _RecordingPublisher:
    def __init__(self) -> None:
        self.messages: list[BaseModel] = []

    def publish(self, message: BaseModel, _settings: WorkerSettings) -> None:
        self.messages.append(message)


def test_wind_to_head_advances_cursor_and_publishes_spec_scan(tmp_path: Path) -> None:
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
    publisher = _RecordingPublisher()
    handler = WindToHeadHandler(settings=settings, publisher=publisher)

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

    with patch(
        "specvsreality_worker.handlers.wind_to_head.sync_commit_artifacts",
        return_value=(commit_context, changes),
    ):
        handler.handle(WindToHeadMessage(repo_id=str(repo_id)))

    with Session(bind=engine) as session:
        updated = session.get(GitRepo, repo_id)
        assert updated is not None
        assert updated.cursor_position == second_sha

    assert len(publisher.messages) == 1
    assert isinstance(publisher.messages[0], SpecScanMessage)
    assert publisher.messages[0].repo_id == str(repo_id)
    assert publisher.messages[0].commit_id == 99
    assert publisher.messages[0].spec_folder == "specs/feature"
