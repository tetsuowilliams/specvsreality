"""Unit tests for SpecDetection."""

from __future__ import annotations

from specvsreality_worker.core.spec_detection import ArtifactType, SpecDetection


def test_is_spec_file_matches_known_filenames_case_insensitively() -> None:
    detection = SpecDetection()

    assert detection.is_spec_file("specs/foo/spec.md")
    assert detection.is_spec_file("specs/foo/SPEC.MD")
    assert detection.is_spec_file("specs/foo/plan.md")
    assert detection.is_spec_file("specs/foo/tasks.md")
    assert not detection.is_spec_file("docs/feature.spec.md")
    assert not detection.is_spec_file("src/main.py")


def test_get_parent_spec_folder_returns_immediate_parent_name() -> None:
    detection = SpecDetection()

    assert detection.get_parent_spec_folder("specs/feature/spec.md") == "feature"
    assert detection.get_parent_spec_folder("spec.md") is None


def test_artifact_type_maps_spec_and_code() -> None:
    detection = SpecDetection()

    assert detection.artifact_type("specs/feature/spec.md") == ArtifactType.SPEC
    assert detection.artifact_type("src/main.py") == ArtifactType.CODE


def test_is_tracked_path_includes_specs_and_code_outside_tooling_dirs() -> None:
    detection = SpecDetection()

    assert detection.is_tracked_path("specs/feature/spec.md")
    assert detection.is_tracked_path("src/main.py")
    assert detection.is_tracked_path("README.md")
    assert detection.is_tracked_path("docs/feature.spec.md")


def test_is_tracked_path_excludes_tooling_directories() -> None:
    detection = SpecDetection()

    assert not detection.is_tracked_path(".cursor/rules/foo.md")
    assert not detection.is_tracked_path(".specify/templates/spec.md")
    assert not detection.is_tracked_path(".skills/my-skill/SKILL.md")
    assert not detection.is_tracked_path("src/.cursor/hidden.py")
