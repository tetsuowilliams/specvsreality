"""Route wiring for gantt chart (stub facade, no database)."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi.testclient import TestClient

from specvsreality_api.facades.gantt_chart_facade import get_gantt_chart_facade
from specvsreality_api.main import create_app
from specvsreality_api.routes import health
from specvsreality_api.schemas.gantt import (
    GanttArtifactBlock,
    GanttChartMeta,
    GanttChartResponse,
    GanttHistorySegment,
    GanttRequirementBlock,
)
from specvsreality_api.schemas.requirement_latest_version import RequirementLatestVersionResponse

_STUB_TS = datetime(2026, 1, 1, tzinfo=UTC)


class _StubGanttFacade:
    def get_requirement_latest_version(
        self,
        repo_id: int,
        spec_id: int,
        *,
        requirement_id: int | None = None,
    ) -> RequirementLatestVersionResponse:
        return RequirementLatestVersionResponse(
            paper_id="stub",
            requirement_text="stub body",
            commit_id="a" * 40,
            commit_datetime=_STUB_TS,
        )

    def get_chart(
        self,
        repo_id: int,
        spec_id: int,
        *,
        requirement_id: int | None = None,
        now: datetime | None = None,
    ) -> GanttChartResponse:
        t0 = datetime(2026, 1, 1, tzinfo=UTC)
        t1 = datetime(2026, 2, 1, tzinfo=UTC)
        return GanttChartResponse(
            meta=GanttChartMeta(requirement_implemented=True),
            requirement=GanttRequirementBlock(
                paper_id="stub",
                history=[
                    GanttHistorySegment(
                        start=t0,
                        end=t1,
                        status="implemented",
                        commit=None,
                    )
                ],
            ),
            artifacts=[
                GanttArtifactBlock(
                    filepath="x.py",
                    history=[
                        GanttHistorySegment(
                            start=t0,
                            end=t1,
                            status="active",
                            commit="f" * 40,
                        )
                    ],
                )
            ],
        )


def test_get_requirement_latest_version_route_with_stub_facade() -> None:
    app = create_app()

    async def _noop_rabbit() -> None:
        return None

    app.dependency_overrides[health.verify_rabbit_reachable] = _noop_rabbit
    app.dependency_overrides[get_gantt_chart_facade] = lambda: _StubGanttFacade()
    try:
        with TestClient(app) as client:
            r = client.get("/repos/1/specs/2/requirements/latest-version?requirement_id=9")
            assert r.status_code == 200
            body = r.json()
            assert body["paper_id"] == "stub"
            assert body["requirement_text"] == "stub body"
            assert len(body["commit_id"]) == 40
    finally:
        app.dependency_overrides.clear()


def test_get_gantt_chart_route_with_stub_facade() -> None:
    app = create_app()

    async def _noop_rabbit() -> None:
        return None

    app.dependency_overrides[health.verify_rabbit_reachable] = _noop_rabbit
    app.dependency_overrides[get_gantt_chart_facade] = lambda: _StubGanttFacade()
    try:
        with TestClient(app) as client:
            r = client.get("/repos/1/specs/2/gantt")
            assert r.status_code == 200
            body = r.json()
            assert body["meta"]["requirement_implemented"] is True
            assert body["requirement"]["paper_id"] == "stub"
            assert body["artifacts"][0]["filepath"] == "x.py"
    finally:
        app.dependency_overrides.clear()
