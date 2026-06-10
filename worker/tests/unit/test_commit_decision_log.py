"""Unit tests for commit decision logging."""

from __future__ import annotations

from unittest.mock import MagicMock

from specvsreality_repositories.models.enums import CommitLogAction
from specvsreality_repositories.repos.scan_selection_repo import (
    ImplementationLinkedSpecRow,
    UnderImplementedSpecRow,
)
from specvsreality_worker.core.commit_decision_log import record_scan_decisions
from specvsreality_worker.core.scan_selection import ScanReason, ScanTarget


def test_record_scan_decisions_writes_rows() -> None:
    repo = MagicMock()
    targets = [
        ScanTarget(
            spec_folder="specs/auth",
            extract_spec=True,
            reasons=(ScanReason.NEW_OR_CHANGED,),
        ),
        ScanTarget(
            spec_folder="specs/billing",
            extract_spec=False,
            reasons=(ScanReason.UNDER_IMPLEMENTED, ScanReason.IMPLEMENTATION_LINKED),
        ),
    ]

    record_scan_decisions(
        commit_log_repo=repo,
        commit_id=42,
        targets=targets,
        under_implemented=[
            UnderImplementedSpecRow(
                paper_id="specs/billing",
                tracked=10,
                implemented=4,
                coverage=40.0,
            )
        ],
        implementation_linked=[
            ImplementationLinkedSpecRow(
                paper_id="specs/billing",
                filepaths=("src/billing.py",),
            )
        ],
        changed_spec_folders=["specs/auth"],
    )

    assert repo.append.call_count == 2
    first = repo.append.call_args_list[0].kwargs
    assert first["action"] == CommitLogAction.SPEC_EXTRACT.value
    assert "specs/auth" in first["reasoning"]
    second = repo.append.call_args_list[1].kwargs
    assert second["action"] == CommitLogAction.SPEC_RESCAN.value
    assert "40.0%" in second["reasoning"]
    assert "src/billing.py" in second["reasoning"]
