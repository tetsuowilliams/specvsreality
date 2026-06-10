"""Pure logic for collecting spec scan targets during commit walk."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ScanReason(StrEnum):
    NEW_OR_CHANGED = "new_or_changed"
    UNDER_IMPLEMENTED = "under_implemented"
    IMPLEMENTATION_LINKED = "implementation_linked"


@dataclass(frozen=True, slots=True)
class ScanTarget:
    spec_folder: str
    extract_spec: bool
    reasons: tuple[ScanReason, ...]


def collect_scan_targets(
    *,
    changed_spec_folders: list[str],
    under_implemented_folders: list[str],
    implementation_linked_folders: list[str],
) -> list[ScanTarget]:
    """Merge scan reasons into deduplicated targets; extract wins over re-eval."""
    changed_set = set(changed_spec_folders)
    by_folder: dict[str, set[ScanReason]] = {}

    for folder in changed_spec_folders:
        by_folder.setdefault(folder, set()).add(ScanReason.NEW_OR_CHANGED)

    for folder in under_implemented_folders:
        if folder in changed_set:
            continue
        by_folder.setdefault(folder, set()).add(ScanReason.UNDER_IMPLEMENTED)

    for folder in implementation_linked_folders:
        if folder in changed_set:
            continue
        by_folder.setdefault(folder, set()).add(ScanReason.IMPLEMENTATION_LINKED)

    targets = [
        ScanTarget(
            spec_folder=folder,
            extract_spec=ScanReason.NEW_OR_CHANGED in reasons,
            reasons=tuple(sorted(reasons, key=lambda reason: reason.value)),
        )
        for folder, reasons in by_folder.items()
    ]
    targets.sort(key=lambda target: (not target.extract_spec, target.spec_folder))
    return targets
