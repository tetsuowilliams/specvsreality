from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from git import Repo
from git.exc import GitCommandError
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import InitRepoMessage, WindToHeadMessage
from specvsreality_repositories.models import Base, GitRepo
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.git_clone import clone_url_with_optional_token
from specvsreality_worker.handlers.init_repo import InitRepoHandler


class _RecordingPublisher:
    def __init__(self) -> None:
        self.messages: list[BaseModel] = []

    def publish(self, message: BaseModel, _settings: WorkerSettings) -> None:
        self.messages.append(message)


def test_init_repo_clones_and_publishes_wind_to_head(tmp_path: Path) -> None:
    source_repo_path = tmp_path / "source"
    source_repo_path.mkdir()
    source_repo = Repo.init(str(source_repo_path))
    (source_repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    source_repo.index.add(["README.md"])
    source_repo.index.commit("init")

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__])
    with Session(bind=engine) as session:
        row = GitRepo(
            name="source",
            url=str(source_repo_path),
            cursor_position="",
            location="",
        )
        session.add(row)
        session.commit()
        repo_id = row.id

    clone_root = tmp_path / "clones"
    settings = WorkerSettings(database_url=db_url)
    publisher = _RecordingPublisher()
    handler = InitRepoHandler(
        settings=settings,
        clone_root=clone_root,
        publisher=publisher,
    )
    handler.handle(InitRepoMessage(repo_id=str(repo_id)))

    all_shas = [c.hexsha for c in reversed(list(source_repo.iter_commits()))]
    first_sha = all_shas[0]

    with Session(bind=engine) as session:
        updated = session.get(GitRepo, repo_id)
        assert updated is not None
        assert updated.location == str(clone_root / str(repo_id))
        assert updated.cursor_position == first_sha
        assert updated.clone_error == ""
        assert (clone_root / str(repo_id) / "README.md").exists()

    assert len(publisher.messages) == 1
    assert isinstance(publisher.messages[0], WindToHeadMessage)
    assert publisher.messages[0].repo_id == str(repo_id)


def test_init_repo_persists_clone_error_on_failure(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__])
    with Session(bind=engine) as session:
        row = GitRepo(
            name="broken",
            url="https://example.test/missing.git",
            cursor_position="",
            location="",
        )
        session.add(row)
        session.commit()
        repo_id = row.id

    clone_root = tmp_path / "clones"
    settings = WorkerSettings(database_url=db_url)
    publisher = _RecordingPublisher()
    handler = InitRepoHandler(
        settings=settings,
        clone_root=clone_root,
        publisher=publisher,
    )
    stderr = "fatal: repository 'https://example.test/missing.git/' not found"
    with patch.object(
        Repo,
        "clone_from",
        side_effect=GitCommandError("clone", 128, stderr),
    ):
        handler.handle(InitRepoMessage(repo_id=str(repo_id)))

    with Session(bind=engine) as session:
        updated = session.get(GitRepo, repo_id)
        assert updated is not None
        assert updated.location == ""
        assert updated.cursor_position == ""
        assert "Failed to initialize repository" in updated.clone_error
        assert stderr in updated.clone_error
        assert "GIT_CLONE_TOKEN" in updated.clone_error

    assert publisher.messages == []


def test_init_repo_clears_existing_clone_error_on_success(tmp_path: Path) -> None:
    source_repo_path = tmp_path / "source"
    source_repo_path.mkdir()
    source_repo = Repo.init(str(source_repo_path))
    (source_repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    source_repo.index.add(["README.md"])
    source_repo.index.commit("init")

    db_path = tmp_path / "test.db"
    db_url = f"sqlite:///{db_path}"
    engine = create_engine(db_url, future=True)
    Base.metadata.create_all(engine, tables=[GitRepo.__table__])
    with Session(bind=engine) as session:
        row = GitRepo(
            name="source",
            url=str(source_repo_path),
            cursor_position="",
            location="",
            clone_error="previous failure",
        )
        session.add(row)
        session.commit()
        repo_id = row.id

    clone_root = tmp_path / "clones"
    settings = WorkerSettings(database_url=db_url)
    publisher = _RecordingPublisher()
    handler = InitRepoHandler(
        settings=settings,
        clone_root=clone_root,
        publisher=publisher,
    )
    handler.handle(InitRepoMessage(repo_id=str(repo_id)))

    with Session(bind=engine) as session:
        updated = session.get(GitRepo, repo_id)
        assert updated is not None
        assert updated.clone_error == ""
        assert updated.cursor_position != ""


def test_clone_url_uses_token_for_https() -> None:
    settings = WorkerSettings(git_clone_token="secret-token")
    url = clone_url_with_optional_token("https://github.com/org/repo.git", settings)
    assert url == "https://x-access-token:secret-token@github.com/org/repo.git"


def test_clone_url_keeps_original_when_credentials_already_present() -> None:
    settings = WorkerSettings(git_clone_token="secret-token")
    original = "https://alice:abc@github.com/org/repo.git"
    assert clone_url_with_optional_token(original, settings) == original
