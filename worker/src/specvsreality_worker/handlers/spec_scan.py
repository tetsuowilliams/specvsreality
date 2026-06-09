"""Handler for `SpecScanMessage`."""

from __future__ import annotations

import logging
from typing import ClassVar

from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import SPEC_SCAN_MESSAGE_TYPE, SpecScanMessage
from specvsreality_repositories.repos import (
    GitRepoRepo,
    create_agent_run_metric_repo,
    create_artifact_candidate_repo,
    create_artifact_version_repo,
    create_commit_repo,
    create_implementation_at_commit_repo,
    create_implements_repo,
    create_spec_item_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_worker.agents.artifact_candidate_agent import create_artifact_candidate_agent
from specvsreality_worker.agents.implements_agent import create_implements_agent
from specvsreality_worker.agents.spec_extraction_agent import create_spec_extraction_agent
from specvsreality_worker.config import WorkerSettings, load_settings
from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder
from specvsreality_worker.core.candidate_discovery import CandidateDiscovery
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.implements_evaluation import ImplementsEvaluation
from specvsreality_worker.core.spec_detection import SpecDetection
from specvsreality_worker.core.spec_merge import SpecMerge
from specvsreality_worker.git_adapter import GitAdapter, GitAdapterError
from specvsreality_worker.handlers.protocol import MessageHandler

logger = logging.getLogger(__name__)


class SpecScanHandler(MessageHandler):
    """Extracts one spec folder at a commit and runs downstream evaluation."""

    message_type: ClassVar[str] = SPEC_SCAN_MESSAGE_TYPE

    def __init__(self, settings: WorkerSettings | None = None) -> None:
        self._settings = settings if settings is not None else load_settings()

    def handle(self, message: BaseModel) -> None:
        if not isinstance(message, SpecScanMessage):
            raise TypeError(f"expected SpecScanMessage, got {type(message).__name__}")

        if not self._settings.database_url:
            raise RuntimeError("DATABASE_URL is required for spec_scan")

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

            commit_row = create_commit_repo(session).get_by_id(message.commit_id)
            if commit_row is None:
                raise RuntimeError(f"commit not found: {message.commit_id}")
            if commit_row.repo_id != repo_id:
                raise RuntimeError(
                    f"commit {message.commit_id} does not belong to repo {repo_id}"
                )

            commit = CommitContext(
                repo_id=repo_id,
                commit_id=commit_row.id,
                commit_sha=commit_row.commit_sha,
                commit_datetime=commit_row.committed_at,
                commit_message=commit_row.commit_message,
            )

            try:
                adapter = GitAdapter(repo_row.location)
            except GitAdapterError as exc:
                raise RuntimeError(f"failed to open cloned repo at {repo_row.location}") from exc

            spec_detection = SpecDetection()
            spec_merge = SpecMerge(
                spec_repo=create_spec_repo(session),
                spec_version_repo=create_spec_version_repo(session),
                spec_item_repo=create_spec_item_repo(session),
                spec_extraction_agent=create_spec_extraction_agent(self._settings),
                git_adapter=adapter,
                spec_detection=spec_detection,
            )
            candidate_discovery = CandidateDiscovery(
                artifact_candidate_agent=create_artifact_candidate_agent(self._settings),
                artifact_version_repo=create_artifact_version_repo(session),
                artifact_candidate_repo=create_artifact_candidate_repo(session),
                git_adapter=adapter,
            )
            implements_evaluation = ImplementsEvaluation(
                implements_agent=create_implements_agent(self._settings),
                implementation_at_commit_repo=create_implementation_at_commit_repo(session),
                implements_repo=create_implements_repo(session),
                artifact_version_repo=create_artifact_version_repo(session),
                settings=self._settings,
            )

            metrics = AgentMetricsRecorder(
                repo=create_agent_run_metric_repo(session),
                settings=self._settings,
                repo_id=repo_id,
                commit_id=commit.commit_id,
            )

            work = spec_merge.merge_spec_folder(
                commit=commit,
                folder=message.spec_folder,
                metrics=metrics,
            )
            if work is None:
                logger.info(
                    "spec_scan skip repo_id=%s commit=%s folder=%s (no spec.md)",
                    repo_id,
                    commit.commit_sha[:7],
                    message.spec_folder,
                )
                return

            candidates = candidate_discovery.discover(
                commit=commit,
                work=work,
                metrics=metrics,
            )
            implements_evaluation.evaluate(
                commit=commit,
                work=work,
                candidates=candidates,
                metrics=metrics,
            )

            session.commit()
            logger.info(
                "spec_scan repo_id=%s commit=%s folder=%s spec_version_id=%s",
                repo_id,
                commit.commit_sha[:7],
                message.spec_folder,
                work.spec_version.id,
            )
        finally:
            session.close()
            engine.dispose()
