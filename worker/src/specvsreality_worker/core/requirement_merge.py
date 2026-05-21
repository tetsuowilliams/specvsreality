"""Merge extracted requirements into repository state."""

from __future__ import annotations

from specvsreality_repositories.repos import RequirementRepo, RequirementVersionRepo
from specvsreality_worker.agents.spec_extraction_agent.models import SpecExtractionResult
from specvsreality_repositories.models.spec import Spec
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.tree_scan import TreeScan
from specvsreality_repositories.repos.enums import VersionStatus

import logging

logger = logging.getLogger(__name__)

class RequirementMerge:
    """Handles requirement merge side-effects for extracted specs."""

    def __init__(
        self,
        *,
        requirement_repo: RequirementRepo,
        requirement_version_repo: RequirementVersionRepo,
        tree_scan: TreeScan,
    ) -> None:
        self._requirement_repo = requirement_repo
        self._requirement_version_repo = requirement_version_repo
        self._tree_scan = tree_scan

    def merge_requirements(self,
        *,
        db_spec: Spec,
        extracted_spec: SpecExtractionResult,
        commit: CommitContext,
    ) -> None:
        updated_spec_reqs = {
            requirement.id: requirement.text
            for requirement in extracted_spec.functional_requirements
        }

        all_live_requirements = self._requirement_repo.list_latest_active_for_spec(
            spec_id=db_spec.id
        )

        for functional_requirement in extracted_spec.functional_requirements:
            if functional_requirement.id is None:
                continue

            db_requirement = self._requirement_repo.get_by_spec_and_paper_id(
                spec_id=db_spec.id,
                paper_id=functional_requirement.id,
            )

            # If there is no requirement in the db then its new.
            if db_requirement is None:
                db_requirement = self._requirement_repo.add(
                    spec_id=db_spec.id,
                    paper_id=functional_requirement.id,
                )
                
            # If there is a requirement in the db then we need to check if it has been changed.
            latest_version = self._requirement_version_repo.get_latest_for_requirement(
                requirement_id=db_requirement.id
            )

            # We dont just create new versions for each new commit blindly. For requirements we 
            # we track new, updated and inactive versions (they can stay the same across commits).
            if latest_version is None:
                self._requirement_version_repo.add(
                    requirement_id=db_requirement.id,
                    commit_sha=commit.commit_sha,
                    commit_datetime=commit.commit_datetime,
                    requirement_text=functional_requirement.text,
                    filepath_globs=functional_requirement.path_globs,
                    status=VersionStatus.ACTIVE.value,
                )
            elif latest_version.requirement_text != functional_requirement.text:
                self._requirement_version_repo.add(
                    requirement_id=db_requirement.id,
                    commit_sha=commit.commit_sha,
                    commit_datetime=commit.commit_datetime,
                    requirement_text=functional_requirement.text,
                    filepath_globs=functional_requirement.path_globs,
                    status=VersionStatus.UPDATED.value,
                )

        # Now for every requirement in the db that isnt in the extracted spec mark as inactive.
        for live_requirement in all_live_requirements:
            if live_requirement.paper_id not in updated_spec_reqs:
                self._requirement_version_repo.add(
                    requirement_id=live_requirement.id,
                    commit_sha=commit.commit_sha,
                    commit_datetime=commit.commit_datetime,
                    requirement_text="",
                    filepath_globs=[],
                    status=VersionStatus.INACTIVE.value,
                )
