"""Stage 2: extract specs changed in a commit into spec versions and spec items."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import PurePosixPath

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos import SpecItemRepo, SpecRepo, SpecVersionRepo
from specvsreality_repositories.repos.enums import VersionStatus
from specvsreality_worker.agents.spec_extraction_agent import SpecExtractionAgent
from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.spec_detection import ArtifactType, SpecDetection
from specvsreality_worker.git_adapter import GitAdapter, GitCommitPathInformation

logger = logging.getLogger(__name__)


@dataclass
class SpecWork:
    """A freshly extracted spec version and its items, for downstream stages."""

    spec_version: SpecVersion
    spec_items: list[SpecItem]
    spec_label: str
    spec_md: str
    tasks_md: str | None
    plan_md: str | None


class SpecMerge:
    def __init__(
        self,
        *,
        spec_repo: SpecRepo,
        spec_version_repo: SpecVersionRepo,
        spec_item_repo: SpecItemRepo,
        spec_extraction_agent: SpecExtractionAgent,
        git_adapter: GitAdapter,
        spec_detection: SpecDetection,
    ) -> None:
        self._spec_repo = spec_repo
        self._spec_version_repo = spec_version_repo
        self._spec_item_repo = spec_item_repo
        self._spec_extraction_agent = spec_extraction_agent
        self._git_adapter = git_adapter
        self._spec_detection = spec_detection

    def _changed_spec_folders(self, changes: GitCommitPathInformation) -> list[str]:
        """Distinct spec directories touched in this commit, preserving order."""
        folders: list[str] = []
        seen: set[str] = set()
        for file_change in changes.paths:
            if file_change.artifact_type != ArtifactType.SPEC:
                continue
            parent = str(PurePosixPath(file_change.path.replace("\\", "/")).parent)
            if parent in seen:
                continue
            seen.add(parent)
            folders.append(parent)
        return folders

    def merge_specs(
        self,
        *,
        commit: CommitContext,
        changes: GitCommitPathInformation,
        metrics: AgentMetricsRecorder | None = None,
    ) -> list[SpecWork]:
        spec_folders = self._changed_spec_folders(changes)
        logger.info(
            "merge_specs repo_id=%s commit=%s changed_spec_folders=%s",
            commit.repo_id,
            commit.commit_sha[:7],
            len(spec_folders),
        )

        works: list[SpecWork] = []
        for folder in spec_folders:
            parent_path = PurePosixPath(folder)
            spec_md_path = str(parent_path / "spec.md")
            spec_md = self._git_adapter.file_at_commit_or_none(commit.commit_sha, spec_md_path)
            if spec_md is None:
                logger.info(
                    "merge_specs skip folder=%s commit=%s (no spec.md at commit)",
                    folder,
                    commit.commit_sha[:7],
                )
                continue

            tasks_md = self._git_adapter.file_at_commit_or_none(
                commit.commit_sha, str(parent_path / "tasks.md")
            )
            plan_md = self._git_adapter.file_at_commit_or_none(
                commit.commit_sha, str(parent_path / "plan.md")
            )

            paper_id = parent_path.name or folder
            extracted = self._spec_extraction_agent.extract_spec(
                spec_md=spec_md,
                tasks_md=tasks_md,
                plan_md=plan_md,
                metrics=metrics,
            )

            db_spec = self._spec_repo.get_by_paper_id(paper_id=paper_id, repo_id=commit.repo_id)
            if db_spec is None:
                db_spec = self._spec_repo.add(paper_id=paper_id, repo_id=commit.repo_id)

            spec_version = self._spec_version_repo.add(
                spec_id=db_spec.id,
                commit_id=commit.commit_id,
                title=extracted.title,
                summary=extracted.summary,
                spec_md=spec_md,
                tasks_md=tasks_md,
                plan_md=plan_md,
                created_at=commit.commit_datetime,
                status=VersionStatus.ACTIVE,
            )

            spec_items: list[SpecItem] = []
            for item in extracted.items:
                spec_items.append(
                    self._spec_item_repo.add(
                        spec_version_id=spec_version.id,
                        local_key=item.local_key,
                        item_type=SpecItemType(item.item_type),
                        text=item.text,
                        source_quote=item.source_quote,
                        importance=SpecItemImportance(item.importance),
                        success_criteria=item.success_criteria,
                        failure_criteria=item.failure_criteria,
                    )
                )

            logger.info(
                "merge_specs folder=%s commit=%s spec_version_id=%s spec_items=%s",
                folder,
                commit.commit_sha[:7],
                spec_version.id,
                len(spec_items),
            )
            works.append(
                SpecWork(
                    spec_version=spec_version,
                    spec_items=spec_items,
                    spec_label=paper_id,
                    spec_md=spec_md,
                    tasks_md=tasks_md,
                    plan_md=plan_md,
                )
            )

        return works
