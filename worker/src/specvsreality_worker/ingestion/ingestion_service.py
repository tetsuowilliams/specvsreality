"""Top-level ingestion entry point: walks commits oldest-first."""

from __future__ import annotations

import logging
from collections.abc import Callable

from specvsreality_repositories.models.repository import Repository
from specvsreality_repositories.repos import RepositoryRepo
from specvsreality_worker.domain import CommitRecord
from specvsreality_worker.evaluation import RetroactiveBackfillService
from specvsreality_worker.git import GitClient
from specvsreality_worker.ingestion.commit_processor import CommitProcessor
from specvsreality_worker.ingestion.evaluation_step import EvaluationStep
from specvsreality_worker.ingestion.spec_sync_step import SpecSyncStep

logger = logging.getLogger(__name__)


CommitCallback = Callable[[CommitRecord], None]


class IngestionService:
    """Owns the commit loop only; per-commit logic lives in injected steps.

    The service emits one ``after_commit`` callback per processed commit so
    callers (e.g. :class:`ScanRepoHandler`) can update ``cursor_position`` /
    commit DB transactions on their own cadence.
    """

    def __init__(
        self,
        *,
        git_client: GitClient,
        repository_repo: RepositoryRepo,
        commit_processor: CommitProcessor,
        spec_sync_step: SpecSyncStep,
        evaluation_step: EvaluationStep,
        retroactive_backfill_service: RetroactiveBackfillService | None = None,
    ) -> None:
        self._git = git_client
        self._repository_repo = repository_repo
        self._commit_processor = commit_processor
        self._spec_sync = spec_sync_step
        self._evaluation = evaluation_step
        self._retroactive_backfill = retroactive_backfill_service

    def ingest_repo(
        self,
        *,
        repository: Repository,
        after_commit: CommitCallback | None = None,
    ) -> None:
        for commit in self._git.iter_commits(oldest_first=True):
            tree = self._commit_processor.process(
                repository=repository, commit=commit
            )
            new_requirement_versions = self._spec_sync.process(
                repository=repository, commit=commit, tree=tree
            )
            self._evaluation.process(
                repository=repository, commit=commit, tree=tree
            )

            if self._retroactive_backfill is not None:
                for rv in new_requirement_versions:
                    self._retroactive_backfill.backfill(requirement_version=rv)

            if after_commit is not None:
                after_commit(commit)

            logger.info(
                "ingest commit done repository_id=%s sha=%s new_rvs=%d",
                repository.id,
                commit.sha[:7],
                len(new_requirement_versions),
            )
