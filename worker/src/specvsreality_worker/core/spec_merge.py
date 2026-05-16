"""Merge spec documents across commits."""

from __future__ import annotations
import logging

from pathlib import PurePosixPath
from typing import ClassVar

from specvsreality_worker.agents.implements_agent import ImplementsEvaluationAgent
from specvsreality_worker.agents.spec_extraction_agent import SpecExtractionAgent
from specvsreality_repositories.repos import RequirementVersionRepo, SpecRepo, SpecVersionRepo
from specvsreality_worker.core.artifact_merge import ArtifactMerge
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.requirement_merge import RequirementMerge
from specvsreality_worker.git_adapter import GitAdapter, GitCommitPathInformation

logger = logging.getLogger(__name__)

class SpecMerge:
    SPEC_FILENAMES: ClassVar[frozenset[str]] = frozenset({"plan.md", "tasks.md", "spec.md"})

    def __init__(
        self,
        *,
        spec_repo: SpecRepo,
        spec_version_repo: SpecVersionRepo,
        requirement_version_repo: RequirementVersionRepo,
        requirement_merge: RequirementMerge,
        artifact_merge: ArtifactMerge,
        spec_extraction_agent: SpecExtractionAgent,
        implements_evaluation_agent: ImplementsEvaluationAgent,
        git_adapter: GitAdapter,
    ) -> None:
        self._spec_repo = spec_repo
        self._spec_version_repo = spec_version_repo
        self._requirement_version_repo = requirement_version_repo
        self._requirement_merge = requirement_merge
        self._artifact_merge = artifact_merge
        self._spec_extraction_agent = spec_extraction_agent
        self._implements_evaluation_agent = implements_evaluation_agent
        self._git_adapter = git_adapter

    def _get_parent_spec_folder(self, relpath: str) -> str | None:
        parent = PurePosixPath(relpath.replace("\\", "/")).parent.name
        return parent or None

    def _is_spec_file(self, relpath: str) -> bool:
        basename = PurePosixPath(relpath.replace("\\", "/")).name
        return basename.lower() in self.SPEC_FILENAMES

    def merge_specs(
        self,
        *,
        commit: CommitContext,
        changes: GitCommitPathInformation,
    ) -> None:
        live_files = [p.replace("\\", "/") for p in (changes.new_files + changes.modified_files)]

        logger.info("merge_specs repo_id=%s commit_sha=%s live_files=%s", commit.repo_id, commit.commit_sha, live_files)

        implementation_pairs = []

        for path in live_files:
            if not self._is_spec_file(path):
                continue

            parent_folder = self._get_parent_spec_folder(path)
            if parent_folder is None:
                continue

            parent_path = PurePosixPath(path.replace("\\", "/")).parent
            spec_md_path = str(parent_path / "spec.md")
            tasks_md_path = str(parent_path / "tasks.md")
            plan_md_path = str(parent_path / "plan.md")
            spec_md = self._git_adapter.file_at_commit(commit.commit_sha, spec_md_path)
            tasks_md = self._git_adapter.file_at_commit_or_none(commit.commit_sha, tasks_md_path)
            plan_md = self._git_adapter.file_at_commit_or_none(commit.commit_sha, plan_md_path)
            
            eph_spec = self._spec_extraction_agent.extract_spec(
                spec_md=spec_md,
                tasks_md=tasks_md,
                plan_md=plan_md,
            )

            db_spec = self._spec_repo.get_by_paper_id(
                paper_id=parent_folder,
                repo_id=commit.repo_id,
            )

            if db_spec is None:
                db_spec = self._spec_repo.add(
                    paper_id=parent_folder,
                    repo_id=commit.repo_id,
                )

            self._spec_version_repo.add(
                spec_id=db_spec.id,
                spec_md=spec_md,
                tasks_md=tasks_md,
                plan_md=plan_md,
            )

            implementation_pairs += self._requirement_merge.merge_requirements(
                db_spec=db_spec,
                extracted_spec=eph_spec,
                commit=commit,
            )

        for path in changes.new_files + changes.modified_files:
            if not self._is_spec_file(path):
                continue

            implementation_pairs += self._artifact_merge.merge_new_updated_artifact(
                relpath=path,
                commit=commit
            )

        for path in changes.deleted_files:
            if not self._is_spec_file(path):
                continue

            self._artifact_merge.merge_deleted_artifact(
                relpath=path,
                commit=commit,
            )

        # Dedupe the pairs as there could be crossover from top down and bottom up.
        implementation_pairs = list(dict.fromkeys(implementation_pairs))

        self._artifact_merge.evaluate_and_merge_implementations(
            implementation_pairs=implementation_pairs,
            commit=commit,
        )
        
        return implementation_pairs