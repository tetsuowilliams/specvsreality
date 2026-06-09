"""Sync code artifacts for a single commit."""

from __future__ import annotations

from specvsreality_repositories.repos import CommitRepo
from specvsreality_worker.core.artifact_merge import ArtifactMerge
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.git_adapter import GitAdapter, GitCommitPathInformation


def sync_commit_artifacts(
    adapter: GitAdapter,
    repo_id: int,
    commit_repo: CommitRepo,
    artifact_merge: ArtifactMerge,
    commit_sha: str,
) -> tuple[CommitContext, GitCommitPathInformation]:
    """Bring artifact tables in sync with one commit's code file changes."""
    changes = adapter.changed_paths(commit_sha=commit_sha)

    commit_row = commit_repo.get_or_create(
        repo_id=repo_id,
        commit_sha=commit_sha,
        commit_message=adapter.commit_message(commit_sha),
        committed_at=adapter.commit_datetime(commit_sha),
    )
    commit = CommitContext(
        repo_id=repo_id,
        commit_id=commit_row.id,
        commit_sha=commit_sha,
        commit_datetime=commit_row.committed_at,
        commit_message=commit_row.commit_message,
    )
    artifact_merge.merge_artifacts(changes=changes, commit=commit)
    return commit, changes
