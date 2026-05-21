"""Merge implementation files into artifact versions."""

from __future__ import annotations

from specvsreality_repositories.repos import (
    ArtifactRepo,
    ArtifactVersionRepo,
    RequirementRepo,
    RequirementVersionRepo,
)
from specvsreality_worker.agents.implements_agent import ImplementsEvaluationAgent
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.tree_scan import TreeScan
from specvsreality_worker.git_adapter import GitAdapter
from specvsreality_repositories.repos.enums import VersionStatus
from specvsreality_repositories.repos.implements_repo import ImplementsRepo
from specvsreality_worker.core.spec_detection import SpecDetection
from specvsreality_worker.git_adapter import GitCommitPathInformation
from specvsreality_worker.core.spec_detection import ArtifactType
from specvsreality_worker.git_adapter import PathChangeState


class ArtifactMerge:
    def __init__(
        self,
        *,
        tree_scan: TreeScan,
        git_adapter: GitAdapter,
        artifact_repo: ArtifactRepo,
        artifact_version_repo: ArtifactVersionRepo,
        requirement_repo: RequirementRepo,
        requirement_version_repo: RequirementVersionRepo,
        implements_repo: ImplementsRepo,
        implements_evaluation_agent: ImplementsEvaluationAgent,
        spec_detection: SpecDetection,
    ) -> None:
        self._tree_scan = tree_scan
        self._git_adapter = git_adapter
        self._artifact_repo = artifact_repo
        self._artifact_version_repo = artifact_version_repo
        self._requirement_repo = requirement_repo
        self._requirement_version_repo = requirement_version_repo
        self._implements_repo = implements_repo
        self._implements_evaluation_agent = implements_evaluation_agent
        self._spec_detection = spec_detection

    def merge_artifacts(self, *, changes: GitCommitPathInformation, commit: CommitContext) -> None:
        for path in changes.paths:
            if path.artifact_type != ArtifactType.CODE:
                continue

            relpath = path.path
            artifact = self._artifact_repo.get_by_filepath(filepath=relpath)

            if artifact is None:
                artifact = self._artifact_repo.add(filepath=relpath)

            if path.state == PathChangeState.DELETED:
                content = ""
                status = VersionStatus.DELETED
            elif path.state == PathChangeState.NEW:
                content = self._git_adapter.file_at_commit(commit.commit_sha, relpath)
                status = VersionStatus.ACTIVE
            else:
                content = self._git_adapter.file_at_commit(commit.commit_sha, relpath)
                status = VersionStatus.UPDATED

            self._artifact_version_repo.add(
                artifact_id=artifact.id,
                commit_sha=commit.commit_sha,
                commit_datetime=commit.commit_datetime,
                status=status.value,
                file_content=content,
            )
    