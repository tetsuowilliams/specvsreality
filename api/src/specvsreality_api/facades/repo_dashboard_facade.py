"""Assemble repository dashboard response."""

from __future__ import annotations

from collections import defaultdict

from fastapi import HTTPException
from sqlalchemy.orm import Session

from specvsreality_api.schemas.repo_dashboard import (
    DashboardArtifactActivity,
    DashboardAttentionItem,
    DashboardRecentChange,
    DashboardSpecRow,
    DashboardSummary,
    RepoDashboardResponse,
)
from specvsreality_repositories.models.enums import SpecItemImportance
from specvsreality_repositories.repos import create_repo_dashboard_repo
from specvsreality_repositories.repos.repo_dashboard_repo import (
    LatestEvaluationRow,
    SpecLatestVersionRow,
)


class RepoDashboardFacade:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._repo = create_repo_dashboard_repo(session)

    def get_dashboard(self, *, repo_id: int) -> RepoDashboardResponse:
        git_repo = self._repo.get_repo(repo_id)
        if git_repo is None:
            raise HTTPException(status_code=404, detail="repo not found")

        cursor_commit = self._repo.get_cursor_commit(
            repo_id=repo_id,
            cursor_sha=git_repo.cursor_position,
        )
        latest_commit = self._repo.get_latest_analysed_commit(repo_id=repo_id)
        display_commit = cursor_commit or latest_commit

        spec_rows = self._repo.list_specs_latest_versions(repo_id=repo_id)
        version_ids = [row.version.id for row in spec_rows]
        items = self._repo.list_items_for_versions(version_ids=version_ids)
        items_by_version: dict[int, list] = defaultdict(list)
        for item in items:
            items_by_version[item.spec_version_id].append(item)

        latest_evals = self._repo.list_latest_evaluations_for_repo(repo_id=repo_id)
        eval_by_item_id = {row.spec_item.id: row for row in latest_evals}
        candidate_counts = self._repo.count_candidates_for_versions(version_ids=version_ids)

        spec_table: list[DashboardSpecRow] = []
        tracked_evaluated = 0
        tracked_implemented = 0
        total_missing = 0
        total_low_confidence = 0
        total_candidates = sum(candidate_counts.values())

        for row in spec_rows:
            version_items = items_by_version.get(row.version.id, [])
            tracked_items = [
                item
                for item in version_items
                if self._repo.is_tracked_importance(item.importance)
            ]
            spec_evals = [
                eval_by_item_id[item.id]
                for item in tracked_items
                if item.id in eval_by_item_id
            ]
            satisfied = sum(1 for ev in spec_evals if ev.implementation.implemented)
            missing = sum(
                1
                for ev in spec_evals
                if not ev.implementation.implemented
                and ev.spec_item.importance == SpecItemImportance.MUST
            )
            low_confidence = sum(
                1
                for ev in spec_evals
                if self._repo.is_low_confidence(ev.implementation.confidence)
            )
            last_eval = max(spec_evals, key=lambda ev: ev.commit.committed_at) if spec_evals else None

            tracked_evaluated += len(spec_evals)
            tracked_implemented += satisfied
            total_missing += missing
            total_low_confidence += low_confidence

            status = self._spec_status(
                tracked_items=tracked_items,
                spec_evals=spec_evals,
                version_row=row,
                cursor_commit_id=cursor_commit.id if cursor_commit else None,
            )

            spec_table.append(
                DashboardSpecRow(
                    spec_id=row.spec.id,
                    paper_id=row.spec.paper_id,
                    latest_version_id=row.version.id,
                    latest_commit_sha=row.commit.commit_sha,
                    status=status,
                    satisfied=satisfied,
                    missing=missing,
                    low_confidence=low_confidence,
                    candidate_artifacts=candidate_counts.get(row.version.id, 0),
                    last_evaluated_commit_sha=last_eval.commit.commit_sha if last_eval else None,
                    last_evaluated_at=last_eval.commit.committed_at if last_eval else None,
                )
            )

        coverage = (
            round((tracked_implemented / tracked_evaluated) * 100, 1)
            if tracked_evaluated > 0
            else None
        )

        summary = DashboardSummary(
            specs_tracked=len(spec_rows),
            latest_commit_sha=display_commit.commit_sha if display_commit else None,
            latest_commit_message=display_commit.commit_message if display_commit else None,
            latest_commit_at=display_commit.committed_at if display_commit else None,
            coverage_percent=coverage,
            missing_items=total_missing,
            low_confidence_items=total_low_confidence,
            candidate_artifacts=total_candidates,
        )

        return RepoDashboardResponse(
            repo_id=git_repo.id,
            repo_name=git_repo.name,
            summary=summary,
            specs=spec_table,
            needs_attention=self._needs_attention(
                spec_rows=spec_rows,
                spec_table=spec_table,
                items_by_version=items_by_version,
                eval_by_item_id=eval_by_item_id,
                cursor_commit_id=cursor_commit.id if cursor_commit else None,
            ),
            recent_changes=self._recent_changes(repo_id=repo_id),
            artifact_activity=self._artifact_activity(repo_id=repo_id),
        )

    def _spec_status(
        self,
        *,
        tracked_items: list,
        spec_evals: list[LatestEvaluationRow],
        version_row: SpecLatestVersionRow,
        cursor_commit_id: int | None,
    ) -> str:
        if not spec_evals:
            return "unknown"
        must_missing = any(
            not ev.implementation.implemented
            and ev.spec_item.importance == SpecItemImportance.MUST
            for ev in spec_evals
        )
        if must_missing:
            return "at_risk"
        if cursor_commit_id is not None and version_row.version.commit_id == cursor_commit_id:
            has_cursor_eval = any(
                ev.commit.id == cursor_commit_id for ev in spec_evals
            )
            if not has_cursor_eval:
                return "stale"
        implemented_count = sum(1 for ev in spec_evals if ev.implementation.implemented)
        if implemented_count == len(spec_evals) and tracked_items:
            return "good"
        if implemented_count >= len(spec_evals) * 0.5:
            return "mostly_implemented"
        return "at_risk"

    def _needs_attention(
        self,
        *,
        spec_rows: list[SpecLatestVersionRow],
        spec_table: list[DashboardSpecRow],
        items_by_version: dict[int, list],
        eval_by_item_id: dict[int, LatestEvaluationRow],
        cursor_commit_id: int | None,
    ) -> list[DashboardAttentionItem]:
        attention: list[DashboardAttentionItem] = []
        table_by_spec = {row.spec_id: row for row in spec_table}

        for row in spec_rows:
            table_row = table_by_spec.get(row.spec.id)
            if table_row is None:
                continue
            if table_row.missing > 0:
                attention.append(
                    DashboardAttentionItem(
                        spec_id=row.spec.id,
                        paper_id=row.spec.paper_id,
                        headline=row.spec.paper_id,
                        detail=f"{table_row.missing} mandatory item{'s' if table_row.missing != 1 else ''} missing",
                        severity="high",
                    )
                )
            elif table_row.candidate_artifacts == 0 and items_by_version.get(row.version.id):
                attention.append(
                    DashboardAttentionItem(
                        spec_id=row.spec.id,
                        paper_id=row.spec.paper_id,
                        headline=row.spec.paper_id,
                        detail="No candidate artifacts found",
                        severity="medium",
                    )
                )
            elif table_row.low_confidence > 0:
                low_item = next(
                    (
                        eval_by_item_id[item.id]
                        for item in items_by_version.get(row.version.id, [])
                        if item.id in eval_by_item_id
                        and self._repo.is_low_confidence(
                            eval_by_item_id[item.id].implementation.confidence
                        )
                    ),
                    None,
                )
                detail = (
                    f"1 low-confidence item: {low_item.spec_item.item_type.value.replace('_', ' ')}"
                    if low_item
                    else f"{table_row.low_confidence} low-confidence items"
                )
                attention.append(
                    DashboardAttentionItem(
                        spec_id=row.spec.id,
                        paper_id=row.spec.paper_id,
                        headline=row.spec.paper_id,
                        detail=detail,
                        severity="medium",
                    )
                )
            elif table_row.status == "stale":
                attention.append(
                    DashboardAttentionItem(
                        spec_id=row.spec.id,
                        paper_id=row.spec.paper_id,
                        headline=row.spec.paper_id,
                        detail="Not evaluated at the latest analysed commit",
                        severity="low",
                    )
                )
            elif table_row.status == "unknown":
                attention.append(
                    DashboardAttentionItem(
                        spec_id=row.spec.id,
                        paper_id=row.spec.paper_id,
                        headline=row.spec.paper_id,
                        detail="No evaluations found",
                        severity="low",
                    )
                )

            if cursor_commit_id is not None:
                version_items = items_by_version.get(row.version.id, [])
                has_implemented = any(
                    item.id in eval_by_item_id and eval_by_item_id[item.id].implementation.implemented
                    for item in version_items
                )
                if table_row.candidate_artifacts > 0 and not has_implemented:
                    attention.append(
                        DashboardAttentionItem(
                            spec_id=row.spec.id,
                            paper_id=row.spec.paper_id,
                            headline=row.spec.paper_id,
                            detail="Candidate artifacts found but no implemented items",
                            severity="medium",
                        )
                    )

        return attention[:12]

    def _recent_changes(self, *, repo_id: int) -> list[DashboardRecentChange]:
        recent = self._repo.list_recent_evaluations(repo_id=repo_id, limit=40)
        changes: list[DashboardRecentChange] = []
        seen: set[tuple[int, str, str]] = set()

        for row in recent:
            key = (row.spec.id, row.spec_item.local_key, row.commit.commit_sha)
            if key in seen:
                continue
            seen.add(key)

            prior = self._repo.list_prior_evaluation(
                repo_id=repo_id,
                spec_id=row.spec.id,
                local_key=row.spec_item.local_key,
                before_committed_at=row.commit.committed_at,
            )
            if prior is not None and prior.implementation.implemented != row.implementation.implemented:
                prev_label = "implemented" if prior.implementation.implemented else "missing"
                curr_label = "implemented" if row.implementation.implemented else "missing"
                message = (
                    f"{row.spec.paper_id}: {row.spec_item.local_key} changed "
                    f"{prev_label} → {curr_label}"
                )
            elif prior is None:
                message = (
                    f"{row.spec.paper_id}: {row.spec_item.local_key} evaluated at "
                    f"{row.commit.commit_sha[:7]}"
                )
            else:
                continue

            changes.append(
                DashboardRecentChange(
                    spec_id=row.spec.id,
                    paper_id=row.spec.paper_id,
                    local_key=row.spec_item.local_key,
                    message=message,
                    commit_sha=row.commit.commit_sha,
                    committed_at=row.commit.committed_at,
                )
            )
            if len(changes) >= 8:
                break

        if changes:
            return changes

        grouped: dict[int, list[LatestEvaluationRow]] = defaultdict(list)
        for row in recent:
            grouped[row.spec.id].append(row)
        fallback: list[DashboardRecentChange] = []
        for spec_id, rows in grouped.items():
            implemented = sum(1 for row in rows if row.implementation.implemented)
            missing = len(rows) - implemented
            first = rows[0]
            fallback.append(
                DashboardRecentChange(
                    spec_id=spec_id,
                    paper_id=first.spec.paper_id,
                    local_key=None,
                    message=(
                        f"{first.spec.paper_id} evaluated at {first.commit.commit_sha[:7]}: "
                        f"{implemented} implemented, {missing} missing"
                    ),
                    commit_sha=first.commit.commit_sha,
                    committed_at=first.commit.committed_at,
                )
            )
            if len(fallback) >= 6:
                break
        return fallback

    def _artifact_activity(self, *, repo_id: int) -> list[DashboardArtifactActivity]:
        rows = self._repo.list_artifact_activity(repo_id=repo_id, limit=12)
        activity: list[DashboardArtifactActivity] = []
        for row in rows:
            if row.link_type == "evidence":
                label = f"evidence for {row.item_count} item{'s' if row.item_count != 1 else ''}"
            else:
                paper = row.spec_paper_id or "spec"
                label = f"candidate for {paper}"
            activity.append(
                DashboardArtifactActivity(
                    filepath=row.filepath,
                    link_type=row.link_type,
                    item_count=row.item_count,
                    spec_paper_id=row.spec_paper_id,
                    label=label,
                )
            )
        return activity[:12]
