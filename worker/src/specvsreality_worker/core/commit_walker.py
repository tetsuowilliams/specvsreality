from __future__ import annotations

from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.spec_merge import SpecMerge
from specvsreality_worker.git_adapter import GitAdapter, GitCommitPathInformation
import logging

logger = logging.getLogger(__name__)


class CommitWalker:
    def __init__(self, adapter: GitAdapter, repo_id: int, spec_merge: SpecMerge) -> None:
        self._adapter = adapter
        self._repo_id = repo_id
        self._spec_merge = spec_merge

    def scan_commit(self, commit_sha: str) -> None:
        logger.info(
                "scan_commit repo_id=%s commit_sha=%s",
                self._repo_id,
                commit_sha[:7],
            )
        changes: GitCommitPathInformation = self._adapter.changed_paths(commit_sha)
        
        commit = CommitContext(
            repo_id=self._repo_id,
            commit_sha=commit_sha,
            commit_datetime=self._adapter.commit_datetime(commit_sha),
        )

        self._spec_merge.merge_specs(
            commit=commit,
            changes=changes,
        )



