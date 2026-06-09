"""Stage 3: discover candidate artifacts that may implement a spec version."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from specvsreality_repositories.repos import ArtifactCandidateRepo, ArtifactVersionRepo
from specvsreality_worker.agents.artifact_candidate_agent import (
    ArtifactCandidateAgent,
    CommitToolCache,
    SpecItemContext,
)
from specvsreality_worker.core.agent_metrics import AgentMetricsRecorder
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.spec_merge import SpecWork
from specvsreality_worker.git_adapter import GitAdapter

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ResolvedCandidate:
    """A candidate artifact resolved to a concrete artifact version and its content."""

    artifact_version_id: int
    filepath: str
    content: str


class CandidateDiscovery:
    def __init__(
        self,
        *,
        artifact_candidate_agent: ArtifactCandidateAgent,
        artifact_version_repo: ArtifactVersionRepo,
        artifact_candidate_repo: ArtifactCandidateRepo,
        git_adapter: GitAdapter,
    ) -> None:
        self._artifact_candidate_agent = artifact_candidate_agent
        self._artifact_version_repo = artifact_version_repo
        self._artifact_candidate_repo = artifact_candidate_repo
        self._git_adapter = git_adapter

    def discover(
        self,
        *,
        commit: CommitContext,
        work: SpecWork,
        metrics: AgentMetricsRecorder | None = None,
    ) -> list[ResolvedCandidate]:
        spec_item_contexts = [
            SpecItemContext(
                local_key=item.local_key,
                item_type=item.item_type.value,
                text=item.text,
                success_criteria=list(item.success_criteria or []),
                failure_criteria=list(item.failure_criteria or []),
            )
            for item in work.spec_items
        ]

        result = self._artifact_candidate_agent.discover(
            git_adapter=self._git_adapter,
            commit_sha=commit.commit_sha,
            spec_label=work.spec_label,
            spec_md=work.spec_md,
            tasks_md=work.tasks_md,
            plan_md=work.plan_md,
            spec_items=spec_item_contexts,
            tool_cache=CommitToolCache(),
            metrics=metrics,
        )

        resolved: list[ResolvedCandidate] = []
        seen_filepaths: set[str] = set()
        for candidate in result.candidates:
            filepath = candidate.filepath.replace("\\", "/").strip()
            if not filepath or filepath in seen_filepaths:
                continue
            seen_filepaths.add(filepath)

            artifact_version = (
                self._artifact_version_repo.get_latest_for_artifact_filepath_at_or_before_commit(
                    filepath=filepath,
                    commit_id=commit.commit_id,
                )
            )
            if artifact_version is None:
                logger.warning(
                    "candidate skip spec=%s commit=%s filepath=%s (no artifact version recorded)",
                    work.spec_label,
                    commit.commit_sha[:7],
                    filepath,
                )
                continue

            self._artifact_candidate_repo.add(
                spec_version_id=work.spec_version.id,
                artifact_version_id=artifact_version.id,
                reasoning=candidate.reasoning,
            )
            resolved.append(
                ResolvedCandidate(
                    artifact_version_id=artifact_version.id,
                    filepath=filepath,
                    content=artifact_version.file_content,
                )
            )

        logger.info(
            "candidate_discovery spec=%s commit=%s proposed=%s resolved=%s",
            work.spec_label,
            commit.commit_sha[:7],
            len(result.candidates),
            len(resolved),
        )
        return resolved
