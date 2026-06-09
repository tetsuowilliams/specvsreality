"""Handler for `InitRepoMessage`."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import ClassVar

from git import Repo
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import INIT_REPO_MESSAGE_TYPE, InitRepoMessage, WindToHeadMessage
from specvsreality_repositories.repos import GitRepoRepo
from specvsreality_worker.config import WorkerSettings, load_settings
from specvsreality_worker.git_adapter import GitAdapter, GitAdapterError
from specvsreality_worker.git_clone import clone_url_with_optional_token, format_init_repo_error
from specvsreality_worker.handlers.protocol import MessageHandler
from specvsreality_worker.messaging.publisher import MessagePublisher, PikaMessagePublisher

logger = logging.getLogger(__name__)


class InitRepoHandler(MessageHandler):
    """Clones a tracked repository and seeds its cursor before winding to head."""

    message_type: ClassVar[str] = INIT_REPO_MESSAGE_TYPE

    def __init__(
        self,
        settings: WorkerSettings | None = None,
        clone_root: str | Path | None = None,
        *,
        publisher: MessagePublisher | None = None,
    ) -> None:
        self._settings = settings if settings is not None else load_settings()
        self._clone_root = Path(
            clone_root or self._settings.repo_clone_root,
        ).resolve()
        self._clone_root.mkdir(parents=True, exist_ok=True)
        self._publisher = publisher if publisher is not None else PikaMessagePublisher()

    def handle(self, message: BaseModel) -> None:
        if not isinstance(message, InitRepoMessage):
            raise TypeError(f"expected InitRepoMessage, got {type(message).__name__}")

        if not self._settings.database_url:
            raise RuntimeError("DATABASE_URL is required for init_repo")

        database_url = self._settings.sync_database_url()
        engine = create_engine(database_url, future=True)
        session = Session(bind=engine)
        try:
            repo_id = int(message.repo_id)
            repo_row = GitRepoRepo(session).get_by_id(repo_id)
            if repo_row is None:
                raise RuntimeError(f"git_repo not found: {message.repo_id}")

            repo_row.clone_error = ""
            target_dir = self._clone_root / str(repo_row.id)
            try:
                if target_dir.exists():
                    shutil.rmtree(target_dir)
                clone_url = clone_url_with_optional_token(repo_row.url, self._settings)
                Repo.clone_from(
                    clone_url,
                    str(target_dir),
                    env={"GIT_TERMINAL_PROMPT": "0"},
                )

                repo_row.location = str(target_dir)
                try:
                    adapter = GitAdapter(target_dir)
                    first_sha = next(adapter.iter_commits_since(None), None)
                except GitAdapterError as exc:
                    raise RuntimeError(f"failed to read cloned repo at {target_dir}") from exc
                if first_sha is None:
                    raise RuntimeError(f"cloned repository has no commits: {repo_row.id}")
                repo_row.cursor_position = first_sha
            except Exception as exc:
                repo_row.clone_error = format_init_repo_error(
                    repo_id=repo_row.id,
                    url=repo_row.url,
                    exc=exc,
                )
                session.commit()
                logger.error(
                    "init_repo failed repo_id=%s: %s",
                    repo_row.id,
                    repo_row.clone_error,
                )
                return

            session.commit()
            logger.info(
                "init_repo repo_id=%s location=%s initial_cursor=%s",
                repo_row.id,
                repo_row.location,
                repo_row.cursor_position[:7],
            )

            self._publisher.publish(
                WindToHeadMessage(repo_id=str(repo_row.id)),
                self._settings,
            )
        finally:
            session.close()
            engine.dispose()
