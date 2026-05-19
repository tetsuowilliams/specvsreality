"""Tests for ``SpecDetector``."""

from __future__ import annotations

from specvsreality_worker.domain import TreeEntry
from specvsreality_worker.ingestion_config import SpecPatternConfig
from specvsreality_worker.spec import SpecDetector


def _entries(*paths: str) -> list[TreeEntry]:
    return [TreeEntry(path=p, blob_sha="0" * 40, size_bytes=10) for p in paths]


def test_detects_one_spec_under_parent_folder() -> None:
    detector = SpecDetector(config=SpecPatternConfig())
    out = detector.detect(_entries("specs/auth/spec.md", "specs/auth/plan.md", "src/x.py"))
    assert len(out) == 1
    spec = out[0]
    assert spec.name == "auth"
    assert spec.spec_path == "specs/auth/spec.md"
    assert spec.plan_path == "specs/auth/plan.md"
    assert spec.tasks_path == "specs/auth/tasks.md"


def test_detects_multiple_specs_at_different_paths() -> None:
    detector = SpecDetector(config=SpecPatternConfig())
    out = detector.detect(
        _entries(
            "specs/auth/spec.md",
            "specs/billing/spec.md",
            "src/__init__.py",
        )
    )
    names = sorted(s.name for s in out)
    assert names == ["auth", "billing"]


def test_ignores_spec_md_at_repo_root() -> None:
    detector = SpecDetector(config=SpecPatternConfig())
    out = detector.detect(_entries("spec.md"))
    assert out == []


def test_uses_configured_filenames() -> None:
    detector = SpecDetector(
        config=SpecPatternConfig(
            spec_filename="SPEC.md", plan_filename="PLAN.md", tasks_filename="TASKS.md"
        )
    )
    out = detector.detect(_entries("docs/feature/SPEC.md"))
    assert len(out) == 1
    assert out[0].plan_path == "docs/feature/PLAN.md"


def test_dedupes_repeated_parent() -> None:
    detector = SpecDetector(config=SpecPatternConfig())
    out = detector.detect(
        _entries("specs/auth/spec.md", "specs/auth/spec.md")  # accidentally duplicate
    )
    assert len(out) == 1
