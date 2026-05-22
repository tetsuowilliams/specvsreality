"""Persist implementation evaluations for requirement versions at a commit."""

from __future__ import annotations

import logging

from specvsreality_repositories.repos import (
    ArtifactVersionRepo,
    ImplementationAtCommitRepo,
    ImplementsRepo,
    RequirementRepo,
    RequirementVersionRepo,
    SpecRepo,
    SpecVersionRepo,
)
from specvsreality_worker.agents.implements_agent import ImplementsEvaluationAgent
from specvsreality_worker.agents.implements_agent.tool_cache import CommitToolCache
from specvsreality_worker.agents.implements_agent.models import RequirementJustification
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.git_adapter import GitAdapter

logger = logging.getLogger(__name__)


class Evaluation:
    def __init__(
        self,
        *,
        spec_repo: SpecRepo,
        spec_version_repo: SpecVersionRepo,
        requirement_repo: RequirementRepo,
        requirement_version_repo: RequirementVersionRepo,
        artifact_version_repo: ArtifactVersionRepo,
        implementation_at_commit_repo: ImplementationAtCommitRepo,
        implements_repo: ImplementsRepo,
        implements_evaluation_agent: ImplementsEvaluationAgent,
        git_adapter: GitAdapter,
    ) -> None:
        self._spec_repo = spec_repo
        self._spec_version_repo = spec_version_repo
        self._requirement_repo = requirement_repo
        self._requirement_version_repo = requirement_version_repo
        self._artifact_version_repo = artifact_version_repo
        self._implementation_at_commit_repo = implementation_at_commit_repo
        self._implements_repo = implements_repo
        self._implements_evaluation_agent = implements_evaluation_agent
        self._git_adapter = git_adapter

    def evaluate_commit(self, *, commit: CommitContext) -> None:
        requirement_versions = self._requirement_version_repo.get_versions_at_commit(
            commit_sha=commit.commit_sha,
        )
        total = len(requirement_versions)
        logger.info(
            "evaluate_commit repo_id=%s commit=%s requirement_versions=%s",
            commit.repo_id,
            commit.commit_sha[:7],
            total,
        )
        if total == 0:
            return

        tool_cache = CommitToolCache()
        for index, requirement_version in enumerate(requirement_versions, start=1):
            requirement = self._requirement_repo.get_by_id(requirement_version.requirement_id)

            spec_version = self._spec_version_repo.get_for_spec_at_commit(
                spec_id=requirement.spec_id,
                commit_sha=commit.commit_sha,
            )

            justification = self._implements_evaluation_agent.evaluate(
                git_adapter=self._git_adapter,
                commit_sha=commit.commit_sha,
                spec_md=spec_version.spec_md,
                tasks_md=spec_version.tasks_md,
                plan_md=spec_version.plan_md,
                requirement_id=requirement.paper_id,
                requirement_text=requirement_version.requirement_text,
                path_globs=list(requirement_version.filepath_globs or []),
                tool_cache=tool_cache,
            )
            self._persist_justification(
                commit=commit,
                requirement_version_id=requirement_version.id,
                justification=justification,
            )

    def _persist_justification(
        self,
        *,
        commit: CommitContext,
        requirement_version_id: int,
        justification: RequirementJustification,
    ) -> None:
        implementation = self._implementation_at_commit_repo.upsert_evaluation(
            requirement_version_id=requirement_version_id,
            evaluation_commit_sha=commit.commit_sha,
            implemented=justification.implemented,
            summary=justification.summary,
            gaps=justification.gaps,
            confidence=justification.confidence,
        )

        for evidence in justification.evidence:
            artifact_version = self._artifact_version_repo.get_latest_for_artifact_filepath(
                filepath=evidence.file,
            )
            if artifact_version is None:
                logger.warning(
                    "skip implements evidence requirement_version_id=%s filepath=%s "
                    "(no artifact version; artifact merge may not have recorded this path yet)",
                    requirement_version_id,
                    evidence.file,
                )
                continue

            self._implements_repo.upsert_evidence(
                implementation_at_commit_id=implementation.id,
                artifact_version_id=artifact_version.id,
                evidence_file=evidence.file,
                evidence_line_number=evidence.line_number,
                evidence_snippet=evidence.snippet,
                evidence_relevance=evidence.relevance,
            )
