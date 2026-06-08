from __future__ import annotations

from pathlib import Path

from git import Repo
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import ScanRepoMessage
from specvsreality_repositories.models import Base, GitRepo
from specvsreality_worker.git_adapter import GitAdapter
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.handlers.scan_repo import ScanRepoHandler, _clone_url_with_optional_token


def test_scan_repo_clones_and_updates_db(tmp_path: Path) -> None:
    source_repo_path = tmp_path / "source"
    source_repo_path.mkdir()
    source_repo = Repo.init(str(source_repo_path))
    (source_repo_path / "README.md").write_text("hello\n", encoding="utf-8")
    source_repo.index.add(["README.md"])
    source_repo.index.commit("init")
    (source_repo_path / "second.txt").write_text("more\n", encoding="utf-8")
    source_repo.index.add(["second.txt"])
    source_repo.index.commit("second")

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

    scanned: list[str] = []

    class _RecordingWalker:
        def __init__(self, adapter, repo_id: int, session: Session, _settings: WorkerSettings) -> None:
            pass

        def scan_commit(self, commit_sha: str) -> None:
            scanned.append(commit_sha)

    handler = ScanRepoHandler(
        settings=settings,
        clone_root=clone_root,
        commit_walker_factory=_RecordingWalker,
    )
    handler.handle(ScanRepoMessage(repo_id=str(repo_id)))

    all_shas = [c.hexsha for c in reversed(list(source_repo.iter_commits()))]
    expected_tip = all_shas[-1]

    with Session(bind=engine) as session:
        updated = session.get(GitRepo, repo_id)
        assert updated is not None
        assert updated.location == str(clone_root / str(repo_id))
        assert updated.cursor_position == expected_tip
        assert (
            list(GitAdapter(updated.location).iter_commits_since(None))[-1]
            == expected_tip
        )
        assert (clone_root / str(repo_id) / "README.md").exists()

    assert scanned == all_shas[1:]


def test_clone_url_uses_token_for_https() -> None:
    settings = WorkerSettings(git_clone_token="secret-token")
    url = _clone_url_with_optional_token("https://github.com/org/repo.git", settings)
    assert url == "https://x-access-token:secret-token@github.com/org/repo.git"


def test_clone_url_keeps_original_when_credentials_already_present() -> None:
    settings = WorkerSettings(git_clone_token="secret-token")
    original = "https://alice:abc@github.com/org/repo.git"
    assert _clone_url_with_optional_token(original, settings) == original

