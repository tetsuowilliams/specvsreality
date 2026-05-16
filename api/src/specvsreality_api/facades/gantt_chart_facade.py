"""Assemble gantt chart payload from repository reads."""

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
from specvsreality_api.schemas.requirement_latest_version import RequirementLatestVersionResponse
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.requirement import Requirement
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.repos import (
    VersionStatus,
    create_gantt_data_repo,
    create_requirement_version_repo,
    create_spec_repo,
)

_STATUS_IMPLEMENTED = "implemented"
_STATUS_NOT_IMPLEMENTED = "not_implemented"


def _requirement_segment_status(
    *,
    requirement_version_id: int,
    artifact_versions_by_rv: dict[int, list[ArtifactVersion]],
) -> str:
    for av in artifact_versions_by_rv.get(requirement_version_id, ()):
        if av.status == VersionStatus.ACTIVE.value:
            return _STATUS_IMPLEMENTED
    return _STATUS_NOT_IMPLEMENTED


def _history_for_requirement_versions(
    versions: list[RequirementVersion],
    *,
    artifact_versions_by_rv: dict[int, list[ArtifactVersion]],
    end_cap: datetime,
) -> list[GanttHistorySegment]:
    if not versions:
        return []
    out: list[GanttHistorySegment] = []
    for i, rv in enumerate(versions):
        start = rv.commit_datetime
        end = versions[i + 1].commit_datetime if i + 1 < len(versions) else end_cap
        status = _requirement_segment_status(
            requirement_version_id=rv.id,
            artifact_versions_by_rv=artifact_versions_by_rv,
        )
        out.append(GanttHistorySegment(start=start, end=end, status=status, commit=None))
    return out


def _history_for_artifact_versions(
    versions: list[ArtifactVersion],
    *,
    end_cap: datetime,
) -> list[GanttHistorySegment]:
    if not versions:
        return []
    out: list[GanttHistorySegment] = []
    for i, av in enumerate(versions):
        start = av.commit_datetime
        end = versions[i + 1].commit_datetime if i + 1 < len(versions) else end_cap
        out.append(
            GanttHistorySegment(
                start=start,
                end=end,
                status=av.status,
                commit=av.commit_id,
            )
        )
    return out


class GanttChartFacade:
    def __init__(self, session: Session) -> None:
        self._spec_repo = create_spec_repo(session)
        self._gantt_data = create_gantt_data_repo(session)
        self._requirement_versions = create_requirement_version_repo(session)

    def _resolved_requirement(
        self,
        repo_id: int,
        spec_id: int,
        requirement_id: int | None,
    ) -> Requirement:
        spec = self._spec_repo.get_by_id(spec_id)
        if spec is None or spec.repo_id != repo_id:
            raise HTTPException(status_code=404, detail="spec not found")

        requirements = self._gantt_data.list_requirements_for_spec_ordered(spec_id=spec_id)
        if not requirements:
            raise HTTPException(status_code=404, detail="no requirement for spec")

        if requirement_id is not None:
            requirement = next((r for r in requirements if r.id == requirement_id), None)
            if requirement is None:
                raise HTTPException(status_code=404, detail="requirement not found for this spec")
            return requirement
        if len(requirements) == 1:
            return requirements[0]
        raise HTTPException(
            status_code=400,
            detail="requirement_id query parameter is required when the spec has more than one requirement",
        )

    def get_requirement_latest_version(
        self,
        repo_id: int,
        spec_id: int,
        *,
        requirement_id: int | None = None,
    ) -> RequirementLatestVersionResponse:
        requirement = self._resolved_requirement(repo_id, spec_id, requirement_id)
        rv = self._requirement_versions.get_latest_for_requirement(requirement_id=requirement.id)
        if rv is None:
            raise HTTPException(status_code=404, detail="no requirement version found")
        return RequirementLatestVersionResponse(
            paper_id=requirement.paper_id,
            requirement_text=rv.requirement_text,
            commit_id=rv.commit_id,
            commit_datetime=rv.commit_datetime,
        )

    def get_chart(
        self,
        repo_id: int,
        spec_id: int,
        *,
        requirement_id: int | None = None,
        now: datetime | None = None,
    ) -> GanttChartResponse:
        effective_now = now if now is not None else datetime.now(UTC)
        if effective_now.tzinfo is None:
            effective_now = effective_now.replace(tzinfo=UTC)

        requirement = self._resolved_requirement(repo_id, spec_id, requirement_id)

        req_versions = self._gantt_data.list_requirement_versions_ordered(
            requirement_id=requirement.id,
        )
        rv_ids = [rv.id for rv in req_versions]
        impl_rows = self._gantt_data.list_implements_with_artifact_versions(
            requirement_version_ids=rv_ids,
        )

        artifact_versions_by_rv: dict[int, list[ArtifactVersion]] = defaultdict(list)
        filepath_by_artifact_id: dict[int, str] = {}
        for _impl, av, art in impl_rows:
            artifact_versions_by_rv[_impl.requirement_version_id].append(av)
            filepath_by_artifact_id[av.artifact_id] = art.filepath

        req_history = _history_for_requirement_versions(
            req_versions,
            artifact_versions_by_rv=artifact_versions_by_rv,
            end_cap=effective_now,
        )
        last_status = req_history[-1].status if req_history else _STATUS_NOT_IMPLEMENTED
        meta = GanttChartMeta(
            requirement_implemented=(last_status == _STATUS_IMPLEMENTED),
        )

        requirement_block = GanttRequirementBlock(
            paper_id=requirement.paper_id,
            history=req_history,
        )

        artifact_ids = sorted(
            filepath_by_artifact_id.keys(),
            key=lambda aid: filepath_by_artifact_id[aid],
        )
        all_versions = self._gantt_data.list_artifact_versions_for_artifact_ids_ordered(
            artifact_ids=artifact_ids,
        )
        versions_by_artifact: dict[int, list[ArtifactVersion]] = defaultdict(list)
        for av in all_versions:
            versions_by_artifact[av.artifact_id].append(av)

        artifacts: list[GanttArtifactBlock] = []
        for aid in artifact_ids:
            fp = filepath_by_artifact_id[aid]
            segs = _history_for_artifact_versions(
                versions_by_artifact.get(aid, []),
                end_cap=effective_now,
            )
            artifacts.append(GanttArtifactBlock(filepath=fp, history=segs))

        return GanttChartResponse(meta=meta, requirement=requirement_block, artifacts=artifacts)


def create_gantt_chart_facade(session: Session) -> GanttChartFacade:
    return GanttChartFacade(session)


def get_gantt_chart_facade(
    session: Annotated[Session, Depends(get_session)],
) -> GanttChartFacade:
    return create_gantt_chart_facade(session)
