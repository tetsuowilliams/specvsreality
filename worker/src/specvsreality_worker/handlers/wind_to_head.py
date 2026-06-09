"""Handler for `WindToHeadMessage`."""

from __future__ import annotations

import logging
from typing import ClassVar

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import (
    WIND_TO_HEAD_MESSAGE_TYPE,
    SpecScanMessage,
    WindToHeadMessage,
)
from specvsreality_repositories.repos import (
    GitRepoRepo,
    create_artifact_repo,
    create_artifact_version_repo,
    create_commit_repo,
)
from specvsreality_worker.config import WorkerSettings, load_settings
from specvsreality_worker.core.artifact_merge import ArtifactMerge
from specvsreality_worker.core.commit_sync import sync_commit_artifacts
from specvsreality_worker.core.spec_merge import changed_spec_folders
from specvsreality_worker.git_adapter import GitAdapter, GitAdapterError
from specvsreality_worker.handlers.protocol import MessageHandler
from specvsreality_worker.messaging.publisher import MessagePublisher, PikaMessagePublisher

logger = logging.getLogger(__name__)


class WindToHeadHandler(MessageHandler):
    """Pulls latest changes and walks commits, syncing code artifacts only."""

    message_type: ClassVar[str] = WIND_TO_HEAD_MESSAGE_TYPE

    def __init__(
        self,
        settings: WorkerSettings | None = None,
        *,
        publisher: MessagePublisher | None = None,
    ) -> None:
        self._settings = settings if settings is not None else load_settings()
        self._publisher = publisher if publisher is not None else PikaMessagePublisher()

    def handle(self, message: BaseModel) -> None:
        if not isinstance(message, WindToHeadMessage):
            raise TypeError(f"expected WindToHeadMessage, got {type(message).__name__}")

        if not self._settings.database_url:
            raise RuntimeError("DATABASE_URL is required for wind_to_head")

        database_url = self._settings.sync_database_url()
        engine = create_engine(database_url, future=True)
        session = Session(bind=engine)
        try:
            repo_id = int(message.repo_id)
            repo_row = GitRepoRepo(session).get_by_id(repo_id)
            if repo_row is None:
                raise RuntimeError(f"git_repo not found: {message.repo_id}")
            if not repo_row.location:
                raise RuntimeError(f"git_repo not initialized (missing location): {repo_row.id}")
            if not repo_row.cursor_position:
                raise RuntimeError(f"git_repo not initialized (missing cursor): {repo_row.id}")

            try:
                adapter = GitAdapter(repo_row.location)
                adapter.pull_default_branch()
            except GitAdapterError as exc:
                raise RuntimeError(f"failed to open cloned repo at {repo_row.location}") from exc

            commit_repo = create_commit_repo(session)
            artifact_merge = ArtifactMerge(
                git_adapter=adapter,
                artifact_repo=create_artifact_repo(session),
                artifact_version_repo=create_artifact_version_repo(session),
            )

            since = repo_row.cursor_position
            for commit_sha in adapter.iter_commits_since(since):
                session.refresh(repo_row)
                commit, changes = sync_commit_artifacts(
                    adapter,
                    repo_id,
                    commit_repo,
                    artifact_merge,
                    commit_sha,
                )
                folders = changed_spec_folders(changes)

                repo_row.cursor_position = commit_sha
                session.commit()
                logger.debug(
                    "wind_to_head repo_id=%s cursor=%s spec_folders=%s",
                    repo_row.id,
                    commit_sha[:7],
                    len(folders),
                )

                for folder in folders:
                    self._publisher.publish(
                        SpecScanMessage(
                            repo_id=str(repo_id),
                            commit_id=commit.commit_id,
                            spec_folder=folder,
                        ),
                        self._settings,
                    )

            logger.info(
                "wind_to_head repo_id=%s done cursor=%s",
                repo_row.id,
                repo_row.cursor_position[:7],
            )
        finally:
            session.close()
            engine.dispose()
