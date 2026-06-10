"""Handler for `WindToHeadMessage`."""

from __future__ import annotations

import asyncio
import logging
from typing import ClassVar

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import WIND_TO_HEAD_MESSAGE_TYPE, WindToHeadMessage
from specvsreality_repositories.repos import (
    GitRepoRepo,
    create_artifact_repo,
    create_artifact_version_repo,
    create_commit_log_repo,
    create_commit_repo,
    create_scan_selection_repo,
)
from specvsreality_worker.config import WorkerSettings, load_settings
from specvsreality_worker.core.artifact_merge import ArtifactMerge
from specvsreality_worker.core.commit_decision_log import record_scan_decisions
from specvsreality_worker.core.commit_sync import sync_commit_artifacts
from specvsreality_worker.core.scan_selection import collect_scan_targets
from specvsreality_worker.core.spec_merge import changed_spec_folders
from specvsreality_worker.core.spec_scanner import SpecScanner
from specvsreality_worker.git_adapter import GitAdapter, GitAdapterError
from specvsreality_worker.handlers.protocol import MessageHandler

logger = logging.getLogger(__name__)


class WindToHeadHandler(MessageHandler):
    """Pulls latest changes and walks commits, syncing artifacts and scanning specs."""

    message_type: ClassVar[str] = WIND_TO_HEAD_MESSAGE_TYPE

    def __init__(
        self,
        settings: WorkerSettings | None = None,
        *,
        spec_scanner: SpecScanner | None = None,
    ) -> None:
        self._settings = settings if settings is not None else load_settings()
        self._spec_scanner = spec_scanner

    def handle(self, message: BaseModel) -> None:
        if not isinstance(message, WindToHeadMessage):
            raise TypeError(f"expected WindToHeadMessage, got {type(message).__name__}")
        asyncio.run(self.handle_async(message))

    async def handle_async(self, message: WindToHeadMessage) -> None:
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
            scan_selection_repo = create_scan_selection_repo(session)
            commit_log_repo = create_commit_log_repo(session)
            artifact_merge = ArtifactMerge(
                git_adapter=adapter,
                artifact_repo=create_artifact_repo(session),
                artifact_version_repo=create_artifact_version_repo(session),
            )
            spec_scanner = (
                self._spec_scanner
                if self._spec_scanner is not None
                else SpecScanner(
                    settings=self._settings,
                    session=session,
                    git_adapter=adapter,
                )
            )

            since = repo_row.cursor_position
            threshold = self._settings.under_implemented_coverage_threshold
            for commit_sha in adapter.iter_commits_since(since):
                session.refresh(repo_row)
                commit, changes = sync_commit_artifacts(
                    adapter,
                    repo_id,
                    commit_repo,
                    artifact_merge,
                    commit_sha,
                )
                changed_folders = changed_spec_folders(changes)
                under_implemented = scan_selection_repo.list_under_implemented_specs_at_commit(
                    repo_id=repo_id,
                    commit_id=commit.commit_id,
                    coverage_threshold=threshold,
                )
                implementation_linked = (
                    scan_selection_repo.list_specs_for_changed_artifacts_at_commit(
                        commit_id=commit.commit_id,
                    )
                )
                targets = collect_scan_targets(
                    changed_spec_folders=changed_folders,
                    under_implemented_folders=[row.paper_id for row in under_implemented],
                    implementation_linked_folders=[
                        row.paper_id for row in implementation_linked
                    ],
                )

                record_scan_decisions(
                    commit_log_repo=commit_log_repo,
                    commit_id=commit.commit_id,
                    targets=targets,
                    under_implemented=under_implemented,
                    implementation_linked=implementation_linked,
                    changed_spec_folders=changed_folders,
                )

                logger.debug(
                    "wind_to_head repo_id=%s commit=%s spec_scans=%s",
                    repo_row.id,
                    commit_sha[:7],
                    len(targets),
                )

                for target in targets:
                    try:
                        await spec_scanner.scan_async(
                            commit=commit,
                            spec_folder=target.spec_folder,
                            extract_spec=target.extract_spec,
                        )
                    except Exception:
                        logger.exception(
                            "wind_to_head scan failed repo_id=%s commit=%s folder=%s",
                            repo_row.id,
                            commit_sha[:7],
                            target.spec_folder,
                        )

                repo_row.cursor_position = commit_sha
                session.commit()
                logger.info(
                    "wind_to_head repo_id=%s committed cursor=%s",
                    repo_row.id,
                    commit_sha[:7],
                )

            logger.info(
                "wind_to_head repo_id=%s done cursor=%s",
                repo_row.id,
                repo_row.cursor_position[:7],
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
            engine.dispose()
