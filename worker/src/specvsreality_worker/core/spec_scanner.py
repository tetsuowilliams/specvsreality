"""Run spec extraction and evaluation for one folder at a commit."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from specvsreality_repositories.repos import (
    create_agent_run_metric_repo,
    create_artifact_candidate_repo,
    create_artifact_version_repo,
    create_implementation_at_commit_repo,
    create_implements_repo,
    create_spec_item_repo,
    create_spec_repo,
    create_spec_version_repo,
)
from specvsreality_worker.agents.artifact_candidate_agent import create_artifact_candidate_agent
from specvsreality_worker.agents.implements_agent import create_implements_agent
from specvsreality_worker.agents.spec_extraction_agent import create_spec_extraction_agent
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder
from specvsreality_worker.core.candidate_discovery import CandidateDiscovery
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.implements_evaluation import ImplementsEvaluation
from specvsreality_worker.core.spec_detection import SpecDetection
from specvsreality_worker.core.spec_merge import SpecMerge
from specvsreality_worker.git_adapter import GitAdapter

logger = logging.getLogger(__name__)


class SpecScanner:
    """Extract or load a spec and run candidate discovery plus implements evaluation."""

    def __init__(
        self,
        *,
        settings: WorkerSettings,
        session: Session,
        git_adapter: GitAdapter,
    ) -> None:
        self._settings = settings
        self._session = session
        self._git_adapter = git_adapter
        spec_detection = SpecDetection()
        self._spec_merge = SpecMerge(
            spec_repo=create_spec_repo(session),
            spec_version_repo=create_spec_version_repo(session),
            spec_item_repo=create_spec_item_repo(session),
            spec_extraction_agent=create_spec_extraction_agent(settings),
            git_adapter=git_adapter,
            spec_detection=spec_detection,
        )
        self._candidate_discovery = CandidateDiscovery(
            artifact_candidate_agent=create_artifact_candidate_agent(settings),
            artifact_version_repo=create_artifact_version_repo(session),
            artifact_candidate_repo=create_artifact_candidate_repo(session),
            git_adapter=git_adapter,
        )
        self._implements_evaluation = ImplementsEvaluation(
            implements_agent=create_implements_agent(settings),
            implementation_at_commit_repo=create_implementation_at_commit_repo(session),
            implements_repo=create_implements_repo(session),
            artifact_version_repo=create_artifact_version_repo(session),
            settings=settings,
        )

    async def scan_async(
        self,
        *,
        commit: CommitContext,
        spec_folder: str,
        extract_spec: bool,
    ) -> None:
        metrics = AgentMetricsRecorder(
            repo=create_agent_run_metric_repo(self._session),
            settings=self._settings,
            repo_id=commit.repo_id,
            commit_id=commit.commit_id,
        )

        if extract_spec:
            work = await self._spec_merge.merge_spec_folder_async(
                commit=commit,
                folder=spec_folder,
                metrics=metrics,
            )
        else:
            work = self._spec_merge.load_spec_work_for_evaluation(
                commit=commit,
                folder=spec_folder,
            )
        if work is None:
            logger.info(
                "spec_scan skip repo_id=%s commit=%s folder=%s extract_spec=%s",
                commit.repo_id,
                commit.commit_sha[:7],
                spec_folder,
                extract_spec,
            )
            return

        candidates = await self._candidate_discovery.discover_async(
            commit=commit,
            work=work,
            metrics=metrics,
        )
        await self._implements_evaluation.evaluate_async(
            commit=commit,
            work=work,
            candidates=candidates,
            metrics=metrics,
        )

        logger.info(
            "spec_scan repo_id=%s commit=%s folder=%s spec_version_id=%s",
            commit.repo_id,
            commit.commit_sha[:7],
            spec_folder,
            work.spec_version.id,
        )
