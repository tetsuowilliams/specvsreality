"""Unit tests for scan target collection."""

from __future__ import annotations

from specvsreality_worker.core.scan_selection import ScanReason, collect_scan_targets


def test_collect_scan_targets_new_and_historic() -> None:
    targets = collect_scan_targets(
        changed_spec_folders=["specs/new"],
        under_implemented_folders=["specs/low"],
        implementation_linked_folders=["specs/linked"],
    )
    assert [target.spec_folder for target in targets] == [
        "specs/new",
        "specs/linked",
        "specs/low",
    ]
    assert targets[0].extract_spec is True
    assert targets[0].reasons == (ScanReason.NEW_OR_CHANGED,)
    assert targets[1].extract_spec is False
    assert ScanReason.IMPLEMENTATION_LINKED in targets[1].reasons


def test_collect_scan_targets_excludes_touched_from_historic() -> None:
    targets = collect_scan_targets(
        changed_spec_folders=["specs/a"],
        under_implemented_folders=["specs/a", "specs/b"],
        implementation_linked_folders=["specs/a"],
    )
    assert len(targets) == 2
    assert targets[0].spec_folder == "specs/a"
    assert targets[0].extract_spec is True
    assert targets[1].spec_folder == "specs/b"
    assert targets[1].reasons == (ScanReason.UNDER_IMPLEMENTED,)


def test_collect_scan_targets_merges_overlapping_reasons() -> None:
    targets = collect_scan_targets(
        changed_spec_folders=[],
        under_implemented_folders=["specs/x"],
        implementation_linked_folders=["specs/x"],
    )
    assert len(targets) == 1
    assert targets[0].reasons == (
        ScanReason.IMPLEMENTATION_LINKED,
        ScanReason.UNDER_IMPLEMENTED,
    )
