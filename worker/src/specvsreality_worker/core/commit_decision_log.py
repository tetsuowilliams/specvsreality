"""Record commit-walk scan decisions to the database."""

from __future__ import annotations

from specvsreality_repositories.models.enums import CommitLogAction
from specvsreality_repositories.repos import CommitLogRepo
from specvsreality_repositories.repos.scan_selection_repo import (
    ImplementationLinkedSpecRow,
    UnderImplementedSpecRow,
)
from specvsreality_worker.core.scan_selection import ScanReason, ScanTarget


def record_scan_decisions(
    *,
    commit_log_repo: CommitLogRepo,
    commit_id: int,
    targets: list[ScanTarget],
    under_implemented: list[UnderImplementedSpecRow],
    implementation_linked: list[ImplementationLinkedSpecRow],
    changed_spec_folders: list[str],
) -> None:
    """Persist one log row per scan target before execution."""
    under_by_folder = {row.paper_id: row for row in under_implemented}
    linked_by_folder = {row.paper_id: row for row in implementation_linked}

    for target in targets:
        action = (
            CommitLogAction.SPEC_EXTRACT
            if target.extract_spec
            else CommitLogAction.SPEC_RESCAN
        )
        message = (
            "Launched spec extraction"
            if target.extract_spec
            else "Launched spec rescan"
        )
        reasoning = _build_reasoning(
            target=target,
            under_implemented=under_by_folder.get(target.spec_folder),
            implementation_linked=linked_by_folder.get(target.spec_folder),
            changed_spec_folders=changed_spec_folders,
        )
        commit_log_repo.append(
            commit_id=commit_id,
            action=action.value,
            spec_folder=target.spec_folder,
            message=message,
            reasoning=reasoning,
        )


def _build_reasoning(
    *,
    target: ScanTarget,
    under_implemented: UnderImplementedSpecRow | None,
    implementation_linked: ImplementationLinkedSpecRow | None,
    changed_spec_folders: list[str],
) -> str:
    parts: list[str] = []
    if ScanReason.NEW_OR_CHANGED in target.reasons:
        parts.append(f"Spec folder touched in commit: {target.spec_folder}")
    if ScanReason.UNDER_IMPLEMENTED in target.reasons and under_implemented is not None:
        coverage = under_implemented.coverage
        coverage_text = f"{coverage}%" if coverage is not None else "unknown"
        parts.append(
            f"Coverage {coverage_text} below threshold "
            f"({under_implemented.implemented}/{under_implemented.tracked} tracked items implemented)"
        )
    if ScanReason.IMPLEMENTATION_LINKED in target.reasons and implementation_linked is not None:
        files = ", ".join(implementation_linked.filepaths)
        parts.append(f"Linked code changed: {files}")
    if not parts and target.spec_folder in changed_spec_folders:
        parts.append(f"Spec folder touched in commit: {target.spec_folder}")
    return "; ".join(parts) if parts else f"Scheduled scan for {target.spec_folder}"
