"""Stage 1: merge non-spec files into artifact versions for a commit."""

from __future__ import annotations

import logging

from specvsreality_repositories.repos import ArtifactRepo, ArtifactVersionRepo
from specvsreality_repositories.repos.enums import VersionStatus
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.spec_detection import ArtifactType, SpecDetection
from specvsreality_worker.git_adapter import (
    GitAdapter,
    GitAdapterError,
    GitCommitPathInformation,
    PathChangeState,
)

logger = logging.getLogger(__name__)


class ArtifactMerge:
    """Synchronises the artifact tables with the code files changed in a commit."""

    def __init__(
        self,
        *,
        git_adapter: GitAdapter,
        artifact_repo: ArtifactRepo,
        artifact_version_repo: ArtifactVersionRepo,
        spec_detection: SpecDetection | None = None,
    ) -> None:
        self._git_adapter = git_adapter
        self._artifact_repo = artifact_repo
        self._artifact_version_repo = artifact_version_repo
        self._spec_detection = spec_detection or SpecDetection()

    def merge_artifacts(self, *, changes: GitCommitPathInformation, commit: CommitContext) -> None:
        merged = 0
        for path in changes.paths:
            if path.artifact_type != ArtifactType.CODE:
                continue

            relpath = path.path
            if path.state != PathChangeState.DELETED and not self._spec_detection.is_text_file(
                relpath,
            ):
                logger.debug(
                    "merge_artifacts skip binary repo_id=%s commit=%s path=%s",
                    commit.repo_id,
                    commit.commit_sha[:7],
                    relpath,
                )
                continue

            artifact = self._artifact_repo.get_by_filepath(filepath=relpath)
            if artifact is None:
                artifact = self._artifact_repo.add(filepath=relpath)

            if path.state == PathChangeState.DELETED:
                content = ""
                status = VersionStatus.DELETED
            else:
                try:
                    content = self._git_adapter.file_at_commit(commit.commit_sha, relpath)
                except GitAdapterError:
                    logger.warning(
                        "merge_artifacts skip non-utf8 repo_id=%s commit=%s path=%s",
                        commit.repo_id,
                        commit.commit_sha[:7],
                        relpath,
                    )
                    continue
                status = (
                    VersionStatus.ACTIVE
                    if path.state == PathChangeState.NEW
                    else VersionStatus.UPDATED
                )

            self._artifact_version_repo.add(
                artifact_id=artifact.id,
                commit_id=commit.commit_id,
                status=status.value,
                file_content=content,
            )
            merged += 1

        logger.info(
            "merge_artifacts repo_id=%s commit=%s artifacts=%s",
            commit.repo_id,
            commit.commit_sha[:7],
            merged,
        )
