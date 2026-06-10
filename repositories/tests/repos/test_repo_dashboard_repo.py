"""Tests for `RepoDashboardRepo`."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from specvsreality_repositories.models.enums import AgentName, SpecItemImportance, SpecItemType
from specvsreality_repositories.repos import (
    create_agent_run_metric_repo,
    create_artifact_candidate_repo,
    create_artifact_repo,
    create_artifact_version_repo,
    create_implementation_at_commit_repo,
    create_implements_repo,
    create_repo_dashboard_repo,
    create_spec_item_repo,
)
from specvsreality_repositories.repos.repo_dashboard_repo import RepoDashboardRepo
from specvsreality_repositories.repos.enums import VersionStatus
from tests.fixtures.graph import add_commit, add_git_repo, add_spec, add_spec_version

_DT = datetime(2026, 1, 15, tzinfo=UTC)


def _build_dashboard_graph(db_session: Session) -> dict[str, int | str]:
    git_repo = add_git_repo(
        db_session,
        name="dashboard-repo",
        url="https://example.test/dash.git",
        cursor_position="c" * 40,
    )
    earlier = add_commit(
        db_session,
        repo_id=git_repo.id,
        commit_sha="a" * 40,
        committed_at=_DT,
    )
    later = add_commit(
        db_session,
        repo_id=git_repo.id,
        commit_sha="b" * 40,
        committed_at=_DT + timedelta(days=1),
    )
    spec_a = add_spec(db_session, paper_id="specs/alpha", repo_id=git_repo.id)
    spec_b = add_spec(db_session, paper_id="specs/beta", repo_id=git_repo.id)
    v_a_old = add_spec_version(
        db_session,
        spec_id=spec_a.id,
        commit_id=earlier.id,
        spec_md="# alpha v1",
    )
    v_a_new = add_spec_version(
        db_session,
        spec_id=spec_a.id,
        commit_id=later.id,
        spec_md="# alpha v2",
    )
    v_b = add_spec_version(
        db_session,
        spec_id=spec_b.id,
        commit_id=later.id,
        spec_md="# beta",
    )
    item_a = create_spec_item_repo(db_session).add(
        spec_version_id=v_a_new.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="alpha item",
        source_quote="q",
        importance=SpecItemImportance.MUST,
        success_criteria=[],
        failure_criteria=[],
    )
    item_b = create_spec_item_repo(db_session).add(
        spec_version_id=v_b.id,
        local_key="FR-1",
        item_type=SpecItemType.FUNCTIONAL_BEHAVIOR,
        text="beta item",
        source_quote="q",
        importance=SpecItemImportance.SHOULD,
        success_criteria=[],
        failure_criteria=[],
    )
    iac_a = create_implementation_at_commit_repo(db_session).upsert_evaluation(
        spec_item_id=item_a.id,
        commit_id=later.id,
        implemented=True,
        summary="alpha ok",
        gaps=[],
        confidence=0.9,
    )
    create_implementation_at_commit_repo(db_session).upsert_evaluation(
        spec_item_id=item_a.id,
        commit_id=earlier.id,
        implemented=False,
        summary="alpha old",
        gaps=["gap"],
        confidence=0.3,
    )
    create_implementation_at_commit_repo(db_session).upsert_evaluation(
        spec_item_id=item_b.id,
        commit_id=later.id,
        implemented=False,
        summary="beta low",
        gaps=["missing"],
        confidence=0.5,
    )
    art = create_artifact_repo(db_session).add(filepath="src/auth.py")
    av = create_artifact_version_repo(db_session).add(
        artifact_id=art.id,
        commit_id=later.id,
        status="active",
        file_content="def auth(): pass",
    )
    create_implements_repo(db_session).upsert_evidence(
        implementation_at_commit_id=iac_a.id,
        artifact_version_id=av.id,
        evidence_file="src/auth.py",
        evidence_line_number=1,
        evidence_snippet="def auth",
        evidence_relevance="implements login",
    )
    create_artifact_candidate_repo(db_session).add(
        spec_version_id=v_b.id,
        artifact_version_id=av.id,
        reasoning="candidate link",
    )
    create_agent_run_metric_repo(db_session).record(
        repo_id=git_repo.id,
        commit_id=later.id,
        agent=AgentName.SPEC_EXTRACTION,
        model="openai:gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        cost_usd=Decimal("0.0001"),
        ran_at=_DT,
    )
    return {
        "repo_id": git_repo.id,
        "cursor_sha": "c" * 40,
        "earlier_commit_id": earlier.id,
        "later_commit_id": later.id,
        "spec_a_id": spec_a.id,
        "spec_b_id": spec_b.id,
        "v_a_old_id": v_a_old.id,
        "v_a_new_id": v_a_new.id,
        "v_b_id": v_b.id,
        "item_a_id": item_a.id,
        "item_b_id": item_b.id,
        "iac_a_id": iac_a.id,
    }


def test_get_repo(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    loaded = repo.get_repo(int(ids["repo_id"]))
    assert loaded is not None
    assert loaded.name == "dashboard-repo"
    assert repo.get_repo(999_999_999) is None


def test_get_cursor_commit(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    found = repo.get_cursor_commit(repo_id=int(ids["repo_id"]), cursor_sha=str(ids["cursor_sha"]))
    assert found is None

    add_commit(
        db_session,
        repo_id=int(ids["repo_id"]),
        commit_sha=str(ids["cursor_sha"]),
        committed_at=_DT + timedelta(days=2),
    )
    found = repo.get_cursor_commit(repo_id=int(ids["repo_id"]), cursor_sha=str(ids["cursor_sha"]))
    assert found is not None
    assert found.commit_sha == ids["cursor_sha"]
    assert repo.get_cursor_commit(repo_id=int(ids["repo_id"]), cursor_sha="") is None


def test_get_latest_analysed_commit(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    latest = repo.get_latest_analysed_commit(repo_id=int(ids["repo_id"]))
    assert latest is not None
    assert latest.id == ids["later_commit_id"]


def test_count_specs(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    assert repo.count_specs(repo_id=int(ids["repo_id"])) == 2
    assert repo.count_specs(repo_id=999_999_999) == 0


def test_list_all_spec_versions_for_repo(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    rows = repo.list_all_spec_versions_for_repo(repo_id=int(ids["repo_id"]))
    assert len(rows) == 3
    paper_ids = [row.spec.paper_id for row in rows]
    assert paper_ids == ["specs/alpha", "specs/alpha", "specs/beta"]


def test_list_specs_latest_versions(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    rows = repo.list_specs_latest_versions(repo_id=int(ids["repo_id"]))
    assert len(rows) == 2
    by_paper = {row.spec.paper_id: row.version.id for row in rows}
    assert by_paper["specs/alpha"] == ids["v_a_new_id"]
    assert by_paper["specs/beta"] == ids["v_b_id"]


def test_list_items_for_versions(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    assert repo.list_items_for_versions(version_ids=[]) == []
    items = repo.list_items_for_versions(version_ids=[int(ids["v_a_new_id"]), int(ids["v_b_id"])])
    assert len(items) == 2
    local_keys = {item.local_key for item in items}
    assert local_keys == {"FR-1"}


def test_list_latest_evaluations_for_repo(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    rows = repo.list_latest_evaluations_for_repo(repo_id=int(ids["repo_id"]))
    assert len(rows) == 2
    by_spec = {row.spec.paper_id: row.implementation.summary for row in rows}
    assert by_spec["specs/alpha"] == "alpha ok"
    assert by_spec["specs/beta"] == "beta low"


def test_list_recent_evaluations(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    rows = repo.list_recent_evaluations(repo_id=int(ids["repo_id"]), limit=10)
    assert len(rows) == 3
    assert rows[0].implementation.summary == "beta low"


def test_list_prior_evaluation(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    prior = repo.list_prior_evaluation(
        repo_id=int(ids["repo_id"]),
        spec_id=int(ids["spec_a_id"]),
        local_key="FR-1",
        before_committed_at=_DT + timedelta(days=1),
    )
    assert prior is not None
    assert prior.implementation.summary == "alpha old"
    assert prior.implementation.implemented is False

    missing = repo.list_prior_evaluation(
        repo_id=int(ids["repo_id"]),
        spec_id=int(ids["spec_b_id"]),
        local_key="FR-1",
        before_committed_at=_DT,
    )
    assert missing is None


def test_count_candidates_for_versions(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    assert repo.count_candidates_for_versions(version_ids=[]) == {}
    counts = repo.count_candidates_for_versions(version_ids=[int(ids["v_b_id"])])
    assert counts == {int(ids["v_b_id"]): 1}


def test_list_artifact_activity(db_session: Session) -> None:
    ids = _build_dashboard_graph(db_session)
    repo = create_repo_dashboard_repo(db_session)

    rows = repo.list_artifact_activity(repo_id=int(ids["repo_id"]))
    link_types = {row.link_type for row in rows}
    assert "evidence" in link_types
    assert "candidate" in link_types
    evidence = next(row for row in rows if row.link_type == "evidence")
    assert evidence.filepath == "src/auth.py"
    assert evidence.item_count == 1


def test_static_helpers() -> None:
    assert RepoDashboardRepo.is_tracked_importance(SpecItemImportance.MUST) is True
    assert RepoDashboardRepo.is_tracked_importance(SpecItemImportance.SHOULD) is True
    assert RepoDashboardRepo.is_tracked_importance(SpecItemImportance.OPTIONAL) is False
    assert RepoDashboardRepo.is_low_confidence(0.5) is True
    assert RepoDashboardRepo.is_low_confidence(0.9) is False
    assert RepoDashboardRepo.is_low_confidence(None) is False
