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
from specvsreality_api.schemas.requirement_version_tree import (
    ImplementsEvidenceItem,
    RequirementTreeArtifactVersion,
    RequirementTreeVersion,
    RequirementVersionTreeResponse,
)
from specvsreality_repositories.models.artifact import Artifact
from specvsreality_repositories.models.artifact_version import ArtifactVersion
from specvsreality_repositories.models.implements import Implements
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


def _requirement_segment_status(*, implemented: bool | None) -> str:
    if implemented is True:
        return _STATUS_IMPLEMENTED
    return _STATUS_NOT_IMPLEMENTED


def _history_for_requirement_versions(
    versions: list[RequirementVersion],
    *,
    end_cap: datetime,
) -> list[GanttHistorySegment]:
    if not versions:
        return []
    out: list[GanttHistorySegment] = []
    for i, rv in enumerate(versions):
        start = rv.commit_datetime
        end = versions[i + 1].commit_datetime if i + 1 < len(versions) else end_cap
        status = _requirement_segment_status(implemented=rv.implemented)
        out.append(GanttHistorySegment(start=start, end=end, status=status, commit=None))
    return out


def _requirement_version_at(
    versions: list[RequirementVersion],
    at: datetime,
) -> RequirementVersion | None:
    """Latest requirement version whose commit time is at or before ``at``."""
    active: RequirementVersion | None = None
    for rv in versions:
        if rv.commit_datetime <= at:
            active = rv
    return active


def _artifact_segment_status(
    av: ArtifactVersion,
    *,
    req_versions: list[RequirementVersion],
    rv_by_id: dict[int, RequirementVersion],
    impl_rows: list[tuple[Implements, ArtifactVersion, Artifact]],
) -> str:
    """Resolve gantt color from implements links and RV evaluation, not raw AV lifecycle status."""
    if av.status in (VersionStatus.DELETED.value, VersionStatus.INACTIVE.value):
        return av.status

    def _status_for_rv(rv: RequirementVersion | None) -> str | None:
        if rv is None:
            return None
        if rv.implemented is True:
            return _STATUS_IMPLEMENTED
        if rv.implemented is False:
            return _STATUS_NOT_IMPLEMENTED
        return None

    for impl, linked_av, _art in impl_rows:
        if linked_av.id != av.id:
            continue
        resolved = _status_for_rv(rv_by_id.get(impl.requirement_version_id))
        if resolved is not None:
            return resolved

    for impl, linked_av, _art in impl_rows:
        if linked_av.artifact_id != av.artifact_id or linked_av.commit_sha != av.commit_sha:
            continue
        resolved = _status_for_rv(rv_by_id.get(impl.requirement_version_id))
        if resolved is not None:
            return resolved

    active_rv = _requirement_version_at(req_versions, av.commit_datetime)
    if active_rv is not None and active_rv.implemented is True:
        for impl, linked_av, _art in impl_rows:
            if impl.requirement_version_id != active_rv.id:
                continue
            if linked_av.artifact_id == av.artifact_id:
                return _STATUS_IMPLEMENTED

    return av.status


def _history_for_artifact_versions(
    versions: list[ArtifactVersion],
    *,
    req_versions: list[RequirementVersion],
    rv_by_id: dict[int, RequirementVersion],
    impl_rows: list[tuple[Implements, ArtifactVersion, Artifact]],
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
                status=_artifact_segment_status(
                    av,
                    req_versions=req_versions,
                    rv_by_id=rv_by_id,
                    impl_rows=impl_rows,
                ),
                commit=av.commit_sha,
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
            commit_sha=rv.commit_sha,
            commit_datetime=rv.commit_datetime,
        )

    def get_requirement_version_tree(
        self,
        repo_id: int,
        spec_id: int,
        *,
        requirement_id: int | None = None,
    ) -> RequirementVersionTreeResponse:
        requirement = self._resolved_requirement(repo_id, spec_id, requirement_id)
        req_versions = self._gantt_data.list_requirement_versions_ordered(
            requirement_id=requirement.id,
        )
        rv_ids = [rv.id for rv in req_versions]
        impl_rows = self._gantt_data.list_implements_with_artifact_versions(
            requirement_version_ids=rv_ids,
        )

        artifacts_by_rv: dict[int, list[RequirementTreeArtifactVersion]] = defaultdict(list)
        for impl, av, art in impl_rows:
            artifacts_by_rv[impl.requirement_version_id].append(
                RequirementTreeArtifactVersion(
                    artifact_version_id=av.id,
                    filepath=art.filepath,
                    commit_sha=av.commit_sha,
                    commit_datetime=av.commit_datetime,
                    status=av.status,
                    file_content=av.file_content,
                    evidence=ImplementsEvidenceItem(
                        evidence_file=impl.evidence_file,
                        evidence_line_number=impl.evidence_line_number,
                        evidence_snippet=impl.evidence_snippet,
                        evidence_relevance=impl.evidence_relevance,
                    ),
                )
            )
        for items in artifacts_by_rv.values():
            items.sort(key=lambda item: (item.filepath, item.artifact_version_id))

        versions = [
            RequirementTreeVersion(
                id=rv.id,
                commit_sha=rv.commit_sha,
                commit_datetime=rv.commit_datetime,
                requirement_text=rv.requirement_text,
                filepath_globs=list(rv.filepath_globs),
                status=rv.status,
                implemented=rv.implemented,
                summary=rv.summary,
                gaps=list(rv.gaps) if rv.gaps is not None else None,
                artifact_versions=artifacts_by_rv.get(rv.id, []),
            )
            for rv in reversed(req_versions)
        ]
        return RequirementVersionTreeResponse(paper_id=requirement.paper_id, versions=versions)

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

        rv_by_id = {rv.id: rv for rv in req_versions}
        filepath_by_artifact_id: dict[int, str] = {}
        for _impl, av, art in impl_rows:
            filepath_by_artifact_id[av.artifact_id] = art.filepath

        req_history = _history_for_requirement_versions(
            req_versions,
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
                req_versions=req_versions,
                rv_by_id=rv_by_id,
                impl_rows=impl_rows,
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
