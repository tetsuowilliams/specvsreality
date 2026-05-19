"""Assemble gantt chart payload from the temporal schema."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.deps.session import get_session
from specvsreality_api.schemas.gantt import (
    GanttArtifactBlock,
    GanttChartMeta,
    GanttChartResponse,
    GanttHistorySegment,
    GanttRequirementBlock,
)
from specvsreality_api.schemas.requirement_latest_version import (
    RequirementLatestVersionResponse,
)
from specvsreality_repositories.models.requirement import Requirement
from specvsreality_repositories.repos import (
    GanttDataRepo,
    RepositoryRepo,
    SpecRepo,
    Verdict,
    create_gantt_data_repo,
    create_repository_repo,
    create_spec_repo,
)

_STATUS_IMPLEMENTED = "implemented"
_STATUS_NOT_IMPLEMENTED = "not_implemented"


class GanttChartFacade:
    """Reads the temporal schema and emits the front-end gantt response shape.

    Behaviour, in plain English:

    * One row per requirement: history is segmented per
      ``RequirementVersion`` ordered by its ``SpecVersion.first_seen_at``,
      with ``end`` set to the next version's start (or ``now`` for the latest).
    * A segment is "implemented" when at least one current claim with
      ``verdict=implements`` exists for that requirement version.
    * Artifact blocks are derived by taking blobs implicated in any current
      "implements" claim and emitting one block per distinct path that blob
      has occupied in the repository's commit history. Each block's history
      mirrors the requirement's segment timeline.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._spec_repo: SpecRepo = create_spec_repo(session)
        self._repository_repo: RepositoryRepo = create_repository_repo(session)
        self._gantt: GanttDataRepo = create_gantt_data_repo(session)

    def _resolved_requirement(
        self,
        repo_id: int,
        spec_id: int,
        requirement_id: int | None,
    ) -> Requirement:
        spec = self._spec_repo.get_by_id(spec_id)
        if spec is None or spec.repository_id != repo_id:
            raise HTTPException(status_code=404, detail="spec not found")

        requirements = self._gantt.list_requirements_for_spec_ordered(
            spec_id=spec_id
        )
        if not requirements:
            raise HTTPException(status_code=404, detail="no requirement for spec")

        if requirement_id is not None:
            requirement = next(
                (r for r in requirements if r.id == requirement_id), None
            )
            if requirement is None:
                raise HTTPException(
                    status_code=404,
                    detail="requirement not found for this spec",
                )
            return requirement

        if len(requirements) == 1:
            return requirements[0]

        raise HTTPException(
            status_code=400,
            detail=(
                "requirement_id query parameter is required when the spec has "
                "more than one requirement"
            ),
        )

    def get_requirement_latest_version(
        self,
        repo_id: int,
        spec_id: int,
        *,
        requirement_id: int | None = None,
    ) -> RequirementLatestVersionResponse:
        requirement = self._resolved_requirement(repo_id, spec_id, requirement_id)
        anchored = self._gantt.list_versions_with_anchor_for_requirement(
            requirement_id=requirement.id
        )
        if not anchored:
            raise HTTPException(
                status_code=404, detail="no requirement version found"
            )
        latest_rv, latest_sv = anchored[-1]
        return RequirementLatestVersionResponse(
            paper_id=requirement.external_id,
            requirement_text=latest_rv.content,
            commit_id=latest_sv.first_seen_commit,
            commit_datetime=latest_sv.first_seen_at,
        )

    def get_chart(
        self,
        repo_id: int,
        spec_id: int,
        *,
        requirement_id: int | None = None,
        now: datetime | None = None,
    ) -> GanttChartResponse:
        if self._repository_repo.get_by_id(repo_id) is None:
            raise HTTPException(status_code=404, detail="repo not found")

        effective_now = now if now is not None else datetime.now(UTC)
        if effective_now.tzinfo is None:
            effective_now = effective_now.replace(tzinfo=UTC)

        requirement = self._resolved_requirement(repo_id, spec_id, requirement_id)
        anchored = self._gantt.list_versions_with_anchor_for_requirement(
            requirement_id=requirement.id
        )

        rv_ids = [rv.id for rv, _sv in anchored]
        latest_claims = self._gantt.latest_claims_for_requirement_versions(
            requirement_version_ids=rv_ids,
        )

        implements_blobs_by_rv: dict[int, set[str]] = defaultdict(set)
        for claim in latest_claims:
            if claim.verdict == Verdict.IMPLEMENTS.value:
                implements_blobs_by_rv[claim.requirement_version_id].add(
                    claim.blob_sha
                )

        segments: list[GanttHistorySegment] = []
        for index, (rv, sv) in enumerate(anchored):
            start = sv.first_seen_at
            end = (
                anchored[index + 1][1].first_seen_at
                if index + 1 < len(anchored)
                else effective_now
            )
            status = (
                _STATUS_IMPLEMENTED
                if implements_blobs_by_rv.get(rv.id)
                else _STATUS_NOT_IMPLEMENTED
            )
            segments.append(
                GanttHistorySegment(
                    start=start,
                    end=end,
                    status=status,
                    commit=sv.first_seen_commit,
                    requirement_text=rv.content,
                    blob_sha=None,
                )
            )

        last_status = segments[-1].status if segments else _STATUS_NOT_IMPLEMENTED
        meta = GanttChartMeta(
            requirement_implemented=(last_status == _STATUS_IMPLEMENTED)
        )

        requirement_block = GanttRequirementBlock(
            paper_id=requirement.external_id,
            history=segments,
        )

        all_implements_blobs = {
            blob for blobs in implements_blobs_by_rv.values() for blob in blobs
        }
        paths_by_blob = self._gantt.list_paths_for_blobs_in_repo(
            repository_id=repo_id,
            blob_shas=sorted(all_implements_blobs),
        )

        artifacts = self._build_artifacts(
            anchored=anchored,
            implements_blobs_by_rv=implements_blobs_by_rv,
            paths_by_blob=paths_by_blob,
            end_cap=effective_now,
        )

        return GanttChartResponse(
            meta=meta, requirement=requirement_block, artifacts=artifacts
        )

    @staticmethod
    def _build_artifacts(
        *,
        anchored: list,
        implements_blobs_by_rv: dict[int, set[str]],
        paths_by_blob: dict[str, list[tuple[str, str]]],
        end_cap: datetime,
    ) -> list[GanttArtifactBlock]:
        path_segments: dict[str, list[GanttHistorySegment]] = defaultdict(list)

        for index, (rv, sv) in enumerate(anchored):
            start = sv.first_seen_at
            end = (
                anchored[index + 1][1].first_seen_at
                if index + 1 < len(anchored)
                else end_cap
            )
            blobs = implements_blobs_by_rv.get(rv.id, set())
            seen_paths_in_segment: set[str] = set()
            for blob in blobs:
                for commit_sha, path in paths_by_blob.get(blob, []):
                    if path in seen_paths_in_segment:
                        continue
                    seen_paths_in_segment.add(path)
                    path_segments[path].append(
                        GanttHistorySegment(
                            start=start,
                            end=end,
                            status="active",
                            commit=commit_sha,
                            requirement_text=None,
                            blob_sha=blob,
                        )
                    )

        return [
            GanttArtifactBlock(filepath=path, history=path_segments[path])
            for path in sorted(path_segments.keys())
        ]


def create_gantt_chart_facade(session: Session) -> GanttChartFacade:
    return GanttChartFacade(session)


def get_gantt_chart_facade(
    session: Annotated[Session, Depends(get_session)],
) -> GanttChartFacade:
    return create_gantt_chart_facade(session)
