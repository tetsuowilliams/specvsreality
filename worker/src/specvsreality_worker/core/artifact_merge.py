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
    ) -> None:
        self._tree_scan = tree_scan
        self._git_adapter = git_adapter
        self._artifact_repo = artifact_repo
        self._artifact_version_repo = artifact_version_repo
        self._requirement_repo = requirement_repo
        self._requirement_version_repo = requirement_version_repo
        self._implements_repo = implements_repo
        self._implements_evaluation_agent = implements_evaluation_agent

    def merge_new_updated_artifact(self, *, relpath: str, commit: CommitContext) -> list[tuple[int, str]]:
        implements_pairs = []
        
        rvs = self._requirement_version_repo.list_latest()

        for rv in rvs:
            for glob in rv.filepath_globs:
                if self._tree_scan.is_glob_match(pattern=glob, file_path=relpath):
                    implements_pairs.append((rv.id, relpath))
                    break
        
        return implements_pairs

    def merge_deleted_artifact(self, *, relpath: str, commit: CommitContext) -> None:
        # We add a deleted record if there was a previous record
        av = self._artifact_version_repo.get_latest_for_artifact_filepath(filepath=relpath)
        
        if av is not None:
            self._artifact_version_repo.add(
                artifact_id=av.artifact_id,
                commit_id=commit.commit_sha,
                commit_datetime=commit.commit_datetime,
                status=VersionStatus.DELETED.value,
                file_content="",
            )

    def evaluate_and_merge_implementations(self, *, implementation_pairs: list[tuple[int, str]], commit: CommitContext) -> None:
        for rv_id, artifact_path in implementation_pairs:
            rv = self._requirement_version_repo.get_by_id(rv_id)
            
            if rv is None:
                continue

            artifact_content = self._git_adapter.file_at_commit(commit.commit_sha, artifact_path)

            implementation_result = self._implements_evaluation_agent.evaluate(
                spec_md="",
                tasks_md=None,
                plan_md=None,
                requirement_id=None,
                requirement_text=rv.requirement_text,
                artifact_sources=[(artifact_path, artifact_content)],
            )

            if implementation_result.implements:
                # We defer recording artifacts until we know they implement something. 
                # This way we dont just record all files and versions of them.
                artifact = self._artifact_repo.get_by_filepath(
                    filepath=artifact_path
                )

                if artifact is None:
                    artifact = self._artifact_repo.add(filepath=artifact_path)

                prior_av = self._artifact_version_repo.get_latest_for_artifact_filepath(filepath=artifact_path)
                this_commit_av = self._artifact_version_repo.get_by_filepath_and_commit(
                    filepath=artifact_path, 
                    commit_id=commit.commit_sha
                )

                if this_commit_av is None:
                    if prior_av is None:
                        status = VersionStatus.ACTIVE.value
                    else:
                        status = VersionStatus.UPDATED.value

                    this_commit_av = self._artifact_version_repo.add(
                        artifact_id=artifact.id,
                        commit_id=commit.commit_sha,
                        commit_datetime=commit.commit_datetime,
                        status=status,
                        file_content=artifact_content,
                    )

                self._implements_repo.add(
                    requirement_version_id=rv_id,
                    artifact_version_id=this_commit_av.id,
                )
            else: # Ok, it doesnt implement it. 
                #The only reason we would care about this is if we were recording that we were implementing.
                latest_av = self._artifact_version_repo.get_latest_for_artifact_filepath(
                    filepath=artifact_path
                )

                # If we dont have a record of the artifact version then we can skip.
                if latest_av is None:
                    continue

                # Have we already been here and done this?
                this_commit_av = self._artifact_version_repo.get_by_filepath_and_commit(
                    filepath=artifact_path, 
                    commit_id=commit.commit_sha
                )

                # If we have already recorded the artifact version for this commit then we can skip.
                if this_commit_av is not None:
                    if this_commit_av.commit_id == latest_av.commit_id:
                        continue

                # Do we have a record of the implements for an old version?
                implements_record = self._implements_repo.get_by_requirement_version_and_artifact_version(
                    requirement_version_id=rv_id, 
                    artifact_version_id=latest_av.id
                )

                # If we have a record of the implements for an old version then we need to add a new version (unlinked) to indicate no implementation.
                if implements_record is not None:
                    artifact = self._artifact_repo.get_by_filepath(
                        filepath=artifact_path
                    )
                    
                    self._artifact_version_repo.add(
                        artifact_id=artifact.id,
                        commit_id=commit.commit_sha,
                        commit_datetime=commit.commit_datetime,
                        status=VersionStatus.UPDATED.value,
                        file_content="",
                    )

