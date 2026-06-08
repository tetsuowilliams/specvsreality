"""Walk a repository commit-by-commit through the four evaluation stages."""

from __future__ import annotations

import logging

from specvsreality_repositories.repos import AgentRunMetricRepo, CommitRepo
from specvsreality_worker.config import WorkerSettings
from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder
from specvsreality_worker.core.artifact_merge import ArtifactMerge
from specvsreality_worker.core.candidate_discovery import CandidateDiscovery
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.implements_evaluation import ImplementsEvaluation
from specvsreality_worker.core.spec_merge import SpecMerge
from specvsreality_worker.git_adapter import GitAdapter, GitCommitPathInformation

logger = logging.getLogger(__name__)


class CommitWalker:
    """Per-commit pipeline: sync artifacts, then re-derive specs and their implementations."""

    def __init__(
        self,
        adapter: GitAdapter,
        repo_id: int,
        commit_repo: CommitRepo,
        artifact_merge: ArtifactMerge,
        spec_merge: SpecMerge,
        candidate_discovery: CandidateDiscovery,
        implements_evaluation: ImplementsEvaluation,
        settings: WorkerSettings,
        agent_run_metric_repo: AgentRunMetricRepo,
    ) -> None:
        self._adapter = adapter
        self._repo_id = repo_id
        self._commit_repo = commit_repo
        self._artifact_merge = artifact_merge
        self._spec_merge = spec_merge
        self._candidate_discovery = candidate_discovery
        self._implements_evaluation = implements_evaluation
        self._settings = settings
        self._agent_run_metric_repo = agent_run_metric_repo

    def scan_commit(self, commit_sha: str) -> None:
        logger.info("scan_commit repo_id=%s commit_sha=%s", self._repo_id, commit_sha[:7])

        changes: GitCommitPathInformation = self._adapter.changed_paths(commit_sha=commit_sha)

        commit_row = self._commit_repo.get_or_create(
            repo_id=self._repo_id,
            commit_sha=commit_sha,
            commit_message=self._adapter.commit_message(commit_sha),
            committed_at=self._adapter.commit_datetime(commit_sha),
        )
        commit = CommitContext(
            repo_id=self._repo_id,
            commit_id=commit_row.id,
            commit_sha=commit_sha,
            commit_datetime=commit_row.committed_at,
            commit_message=commit_row.commit_message,
        )

        # Stage 1: bring artifact tables in sync with this commit's code files.
        self._artifact_merge.merge_artifacts(changes=changes, commit=commit)

        metrics = AgentMetricsRecorder(
            repo=self._agent_run_metric_repo,
            settings=self._settings,
            repo_id=self._repo_id,
            commit_id=commit.commit_id,
        )

        # Stages 2-4: only run when a spec changed in this commit.
        works = self._spec_merge.merge_specs(commit=commit, changes=changes, metrics=metrics)

        for work in works:
            candidates = self._candidate_discovery.discover(
                commit=commit,
                work=work,
                metrics=metrics,
            )
            self._implements_evaluation.evaluate(
                commit=commit,
                work=work,
                candidates=candidates,
                metrics=metrics,
            )
