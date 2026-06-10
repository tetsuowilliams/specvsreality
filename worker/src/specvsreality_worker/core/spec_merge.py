"""Stage 2: extract specs changed in a commit into spec versions and spec items."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import PurePosixPath

from specvsreality_repositories.models.enums import SpecItemImportance, SpecItemType
from specvsreality_repositories.models.spec_item import SpecItem
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos import SpecItemRepo, SpecRepo, SpecVersionRepo
from specvsreality_repositories.repos.spec_repo import normalize_spec_folder
from specvsreality_repositories.text_match import compute_highlight_spans
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


def changed_spec_folders(changes: GitCommitPathInformation) -> list[str]:
    """Distinct spec directories touched in this commit, preserving order."""
    folders: list[str] = []
    seen: set[str] = set()
    for file_change in changes.paths:
        if file_change.artifact_type != ArtifactType.SPEC:
            continue
        parent = normalize_spec_folder(
            str(PurePosixPath(file_change.path.replace("\\", "/")).parent)
        )
        if not parent or parent in seen:
            continue
        seen.add(parent)
        folders.append(parent)
    return folders


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

    def merge_specs(
        self,
        *,
        commit: CommitContext,
        changes: GitCommitPathInformation,
        metrics: AgentMetricsRecorder | None = None,
    ) -> list[SpecWork]:
        spec_folders = changed_spec_folders(changes)
        logger.info(
            "merge_specs repo_id=%s commit=%s changed_spec_folders=%s",
            commit.repo_id,
            commit.commit_sha[:7],
            len(spec_folders),
        )

        works: list[SpecWork] = []
        for folder in spec_folders:
            work = self.merge_spec_folder(
                commit=commit,
                folder=folder,
                metrics=metrics,
            )
            if work is not None:
                works.append(work)
        return works

    def merge_spec_folder(
        self,
        *,
        commit: CommitContext,
        folder: str,
        metrics: AgentMetricsRecorder | None = None,
    ) -> SpecWork | None:
        folder = normalize_spec_folder(folder)
        parent_path = PurePosixPath(folder)
        spec_md_path = str(parent_path / "spec.md")
        spec_md = self._git_adapter.file_at_commit_or_none(commit.commit_sha, spec_md_path)
        if spec_md is None:
            logger.info(
                "merge_spec_folder skip folder=%s commit=%s (no spec.md at commit)",
                folder,
                commit.commit_sha[:7],
            )
            return None

        tasks_md = self._git_adapter.file_at_commit_or_none(
            commit.commit_sha, str(parent_path / "tasks.md")
        )
        plan_md = self._git_adapter.file_at_commit_or_none(
            commit.commit_sha, str(parent_path / "plan.md")
        )

        db_spec, _spec_created = self._spec_repo.get_or_create_for_folder(
            folder=folder,
            repo_id=commit.repo_id,
        )

        spec_version, version_created = self._spec_version_repo.get_or_create(
            spec_id=db_spec.id,
            commit_id=commit.commit_id,
            title=None,
            summary=None,
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
            created_at=commit.commit_datetime,
            status=VersionStatus.ACTIVE,
        )
        if not version_created:
            spec_items = self._spec_item_repo.list_for_spec_version(
                spec_version_id=spec_version.id,
            )
            logger.info(
                "merge_spec_folder folder=%s commit=%s reusing spec_version_id=%s items=%s",
                folder,
                commit.commit_sha[:7],
                spec_version.id,
                len(spec_items),
            )
            return SpecWork(
                spec_version=spec_version,
                spec_items=spec_items,
                spec_label=folder,
                spec_md=spec_version.spec_md,
                tasks_md=spec_version.tasks_md,
                plan_md=spec_version.plan_md,
            )

        extracted = self._spec_extraction_agent.extract_spec(
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
            metrics=metrics,
        )

        spec_version.title = extracted.title
        spec_version.summary = extracted.summary

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
                    highlight_spans=compute_highlight_spans(
                        spec_md=spec_md,
                        tasks_md=tasks_md,
                        plan_md=plan_md,
                        source_quote=item.source_quote,
                        text=item.text,
                    ),
                )
            )

        logger.info(
            "merge_spec_folder folder=%s commit=%s spec_version_id=%s spec_items=%s",
            folder,
            commit.commit_sha[:7],
            spec_version.id,
            len(spec_items),
        )
        return SpecWork(
            spec_version=spec_version,
            spec_items=spec_items,
            spec_label=folder,
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
        )

    async def merge_spec_folder_async(
        self,
        *,
        commit: CommitContext,
        folder: str,
        metrics: AgentMetricsRecorder | None = None,
    ) -> SpecWork | None:
        folder = normalize_spec_folder(folder)
        parent_path = PurePosixPath(folder)
        spec_md_path = str(parent_path / "spec.md")
        spec_md = self._git_adapter.file_at_commit_or_none(commit.commit_sha, spec_md_path)
        if spec_md is None:
            logger.info(
                "merge_spec_folder skip folder=%s commit=%s (no spec.md at commit)",
                folder,
                commit.commit_sha[:7],
            )
            return None

        tasks_md = self._git_adapter.file_at_commit_or_none(
            commit.commit_sha, str(parent_path / "tasks.md")
        )
        plan_md = self._git_adapter.file_at_commit_or_none(
            commit.commit_sha, str(parent_path / "plan.md")
        )

        db_spec, _spec_created = self._spec_repo.get_or_create_for_folder(
            folder=folder,
            repo_id=commit.repo_id,
        )

        spec_version, version_created = self._spec_version_repo.get_or_create(
            spec_id=db_spec.id,
            commit_id=commit.commit_id,
            title=None,
            summary=None,
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
            created_at=commit.commit_datetime,
            status=VersionStatus.ACTIVE,
        )
        if not version_created:
            spec_items = self._spec_item_repo.list_for_spec_version(
                spec_version_id=spec_version.id,
            )
            logger.info(
                "merge_spec_folder folder=%s commit=%s reusing spec_version_id=%s items=%s",
                folder,
                commit.commit_sha[:7],
                spec_version.id,
                len(spec_items),
            )
            return SpecWork(
                spec_version=spec_version,
                spec_items=spec_items,
                spec_label=folder,
                spec_md=spec_version.spec_md,
                tasks_md=spec_version.tasks_md,
                plan_md=spec_version.plan_md,
            )

        extracted = await self._spec_extraction_agent.extract_spec_async(
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
            metrics=metrics,
        )

        spec_version.title = extracted.title
        spec_version.summary = extracted.summary

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
                    highlight_spans=compute_highlight_spans(
                        spec_md=spec_md,
                        tasks_md=tasks_md,
                        plan_md=plan_md,
                        source_quote=item.source_quote,
                        text=item.text,
                    ),
                )
            )

        logger.info(
            "merge_spec_folder folder=%s commit=%s spec_version_id=%s spec_items=%s",
            folder,
            commit.commit_sha[:7],
            spec_version.id,
            len(spec_items),
        )
        return SpecWork(
            spec_version=spec_version,
            spec_items=spec_items,
            spec_label=folder,
            spec_md=spec_md,
            tasks_md=tasks_md,
            plan_md=plan_md,
        )

    def load_spec_work_for_evaluation(
        self,
        *,
        commit: CommitContext,
        folder: str,
    ) -> SpecWork | None:
        """Load the effective spec version and items for evaluation without re-extracting."""
        folder = normalize_spec_folder(folder)
        parent_path = PurePosixPath(folder)
        spec_md_path = str(parent_path / "spec.md")
        if self._git_adapter.file_at_commit_or_none(commit.commit_sha, spec_md_path) is None:
            logger.info(
                "load_spec_work skip folder=%s commit=%s (no spec.md at commit)",
                folder,
                commit.commit_sha[:7],
            )
            return None

        db_spec = self._spec_repo.get_by_paper_id(paper_id=folder, repo_id=commit.repo_id)
        if db_spec is None:
            logger.info(
                "load_spec_work skip folder=%s commit=%s (no spec row)",
                folder,
                commit.commit_sha[:7],
            )
            return None

        spec_version = self._spec_version_repo.get_latest_at_or_before_commit(
            spec_id=db_spec.id,
            commit_id=commit.commit_id,
        )
        if spec_version is None:
            logger.info(
                "load_spec_work skip folder=%s commit=%s (no version at or before commit)",
                folder,
                commit.commit_sha[:7],
            )
            return None

        spec_items = self._spec_item_repo.list_for_spec_version(
            spec_version_id=spec_version.id,
        )
        if not spec_items:
            logger.info(
                "load_spec_work skip folder=%s commit=%s spec_version_id=%s (no items)",
                folder,
                commit.commit_sha[:7],
                spec_version.id,
            )
            return None

        logger.info(
            "load_spec_work folder=%s commit=%s spec_version_id=%s items=%s",
            folder,
            commit.commit_sha[:7],
            spec_version.id,
            len(spec_items),
        )
        return SpecWork(
            spec_version=spec_version,
            spec_items=spec_items,
            spec_label=folder,
            spec_md=spec_version.spec_md,
            tasks_md=spec_version.tasks_md,
            plan_md=spec_version.plan_md,
        )
