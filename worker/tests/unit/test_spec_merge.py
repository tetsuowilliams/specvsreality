"""Unit tests for spec merge helpers."""

from __future__ import annotations

from specvsreality_worker.core.spec_merge import spec_folders_to_scan


def test_spec_folders_to_scan_changed_only() -> None:
    scans = spec_folders_to_scan(
        changed_folders=["specs/a"],
        known_spec_folders=["specs/a", "specs/b"],
    )
    assert scans == [("specs/a", True), ("specs/b", False)]


def test_spec_folders_to_scan_dedupes_changed_from_known() -> None:
    scans = spec_folders_to_scan(
        changed_folders=["specs/a"],
        known_spec_folders=["specs/a"],
    )
    assert scans == [("specs/a", True)]


def test_spec_folders_to_scan_no_known_specs() -> None:
    scans = spec_folders_to_scan(
        changed_folders=["specs/new"],
        known_spec_folders=[],
    )
    assert scans == [("specs/new", True)]
