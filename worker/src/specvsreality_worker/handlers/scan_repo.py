"""Handler for `ScanRepoMessage`."""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar
from urllib.parse import quote, urlsplit, urlunsplit

from git import Repo
from git.exc import GitCommandError
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import SCAN_REPO_MESSAGE_TYPE, ScanRepoMessage
from specvsreality_repositories.repos import (
    GitRepoRepo,
    create_artifact_repo,
    create_artifact_version_repo,
    create_implements_repo,
    create_requirement_repo,
    create_requirement_version_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_worker.agents.implements_agent import create_implements_evaluation_agent
from specvsreality_worker.agents.spec_extraction_agent import create_spec_extraction_agent
from specvsreality_worker.core import ArtifactMerge, CommitWalker, RequirementMerge, SpecMerge, TreeScan
from specvsreality_worker.core.evaluation import Evaluation
from specvsreality_worker.core.spec_detection import SpecDetection
from specvsreality_worker.git_adapter import GitAdapter, GitAdapterError
from specvsreality_worker.handlers.protocol import MessageHandler

logger = logging.getLogger(__name__)

CommitWalkerFactory = Callable[[GitAdapter, int, Session], CommitWalker]
SpecMergeFactory = Callable[[Session, GitAdapter], SpecMerge]


def _build_spec_merge(session: Session, adapter: GitAdapter) -> SpecMerge:
    tree_scan = TreeScan(git_adapter=adapter)
    spec_detection = SpecDetection()
    requirement_repo = create_requirement_repo(session)
    requirement_version_repo = create_requirement_version_repo(session)
    implements_agent = create_implements_evaluation_agent()
    artifact_merge = ArtifactMerge(
        tree_scan=tree_scan,
        git_adapter=adapter,
        artifact_repo=create_artifact_repo(session),
        artifact_version_repo=create_artifact_version_repo(session),
        requirement_repo=requirement_repo,
        requirement_version_repo=requirement_version_repo,
        implements_repo=create_implements_repo(session),
        implements_evaluation_agent=implements_agent,
        spec_detection=spec_detection,
    )
    return SpecMerge(
        spec_repo=create_spec_repo(session),
        spec_version_repo=create_spec_version_repo(session),
        requirement_version_repo=requirement_version_repo,
        requirement_merge=RequirementMerge(
            requirement_repo=requirement_repo,
            requirement_version_repo=requirement_version_repo,
            tree_scan=tree_scan,
        ),
        artifact_merge=artifact_merge,
        spec_extraction_agent=create_spec_extraction_agent(),
        implements_evaluation_agent=implements_agent,
        git_adapter=adapter,
        spec_detection=spec_detection,
    )


def _build_commit_walker(adapter: GitAdapter, repo_id: int, session: Session) -> CommitWalker:
    spec_merge = _build_spec_merge(session, adapter)
    evaluation = Evaluation(
        spec_repo=create_spec_repo(session),
        spec_version_repo=create_spec_version_repo(session),
        requirement_repo=create_requirement_repo(session),
        requirement_version_repo=create_requirement_version_repo(session),
        artifact_repo=create_artifact_repo(session),
        artifact_version_repo=create_artifact_version_repo(session),
        implements_repo=create_implements_repo(session),
        implements_evaluation_agent=create_implements_evaluation_agent(),
        git_adapter=adapter,
    )
    return CommitWalker(
        adapter,
        repo_id,
        spec_merge,
        spec_merge._artifact_merge,
        evaluation,
    )


def _sync_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _clone_url_with_optional_token(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    if parsed.scheme != "https":
        return raw_url
    if parsed.username is not None:
        return raw_url

    token = os.getenv("GIT_CLONE_TOKEN", "").strip()
    if not token:
        return raw_url

    username = os.getenv("GIT_CLONE_USERNAME", "x-access-token").strip() or "x-access-token"
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port is not None else ""
    netloc = f"{quote(username)}:{quote(token, safe='')}@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


class ScanRepoHandler(MessageHandler):
    """Clones a tracked repository; walks history and advances ``cursor_position``."""

    message_type: ClassVar[str] = SCAN_REPO_MESSAGE_TYPE

    def __init__(
        self,
        clone_root: str | Path | None = None,
        *,
        spec_merge_factory: SpecMergeFactory = _build_spec_merge,
        commit_walker_factory: CommitWalkerFactory = _build_commit_walker,
    ) -> None:
        self._clone_root = Path(clone_root or os.getenv("REPO_CLONE_ROOT", "/repos")).resolve()
        self._clone_root.mkdir(parents=True, exist_ok=True)
        if spec_merge_factory is None:
            raise ValueError("spec_merge_factory must not be None")
        self._spec_merge_factory = spec_merge_factory
        self._commit_walker_factory = commit_walker_factory

    def handle(self, message: BaseModel) -> None:
        if not isinstance(message, ScanRepoMessage):
            raise TypeError(f"expected ScanRepoMessage, got {type(message).__name__}")

        database_url = _sync_database_url(os.environ["DATABASE_URL"])
        engine = create_engine(database_url, future=True)
        session = Session(bind=engine)
        try:
            repo_id = int(message.repo_id)
            repo_row = GitRepoRepo(session).get_by_id(repo_id)
            if repo_row is None:
                raise RuntimeError(f"git_repo not found: {message.repo_id}")

            target_dir = self._clone_root / str(repo_row.id)
            if target_dir.exists():
                shutil.rmtree(target_dir)
            clone_url = _clone_url_with_optional_token(repo_row.url)
            try:
                Repo.clone_from(
                    clone_url,
                    str(target_dir),
                    env={"GIT_TERMINAL_PROMPT": "0"},
                )
            except GitCommandError as exc:
                msg = (
                    f"failed to clone repo_id={repo_row.id} url={repo_row.url!r}; "
                    "if this repository is private, set GIT_CLONE_TOKEN"
                )
                raise RuntimeError(msg) from exc

            repo_row.location = str(target_dir)
            try:
                adapter = GitAdapter(target_dir)
                first_sha = next(adapter.iter_commits_since(None), None)
            except GitAdapterError as exc:
                raise RuntimeError(f"failed to read cloned repo at {target_dir}") from exc
            if first_sha is None:
                raise RuntimeError(f"cloned repository has no commits: {repo_row.id}")
            repo_row.cursor_position = first_sha

            session.commit()
            logger.info(
                "scan_repo repo_id=%s location=%s initial_cursor=%s",
                repo_row.id,
                repo_row.location,
                first_sha[:7],
            )

            walker = self._commit_walker_factory(adapter, repo_id, session)

            for commit_sha in adapter.iter_commits_since(first_sha):
                session.refresh(repo_row)
                walker.scan_commit(commit_sha)

                repo_row.cursor_position = commit_sha
                session.commit()
                logger.debug(
                    "scan_repo repo_id=%s cursor=%s",
                    repo_row.id,
                    commit_sha[:7],
                )

            logger.info(
                "scan_repo repo_id=%s done cursor=%s",
                repo_row.id,
                repo_row.cursor_position[:7],
            )
        finally:
            session.close()
            engine.dispose()
