"""SpecAnalyser rules and Spec construction."""

from __future__ import annotations

import pytest

from specvsreality_worker.models.spec import Spec
from specvsreality_worker.spec_analyser import SpecAnalyser


@pytest.fixture
def analyser() -> SpecAnalyser:
    return SpecAnalyser()


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("docs/foo.spec.md", True),
        ("foo.spec.yaml", True),
        ("bar.spec.yml", True),
        ("SPEC.md", True),
        ("dir/SPEC.yaml", True),
        ("README.md", False),
        ("foo.md", False),
        ("spec.md", False),
        ("", False),
    ],
)
def test_is_spec_path(analyser: SpecAnalyser, path: str, expected: bool) -> None:
    assert analyser.is_spec_path(path) is expected


def test_build_spec_paths_and_content(analyser: SpecAnalyser) -> None:
    spec = analyser.build_spec(filepath="docs/Auth.spec.md", content="# Auth\n\nRules.\n")
    assert spec.filename == "Auth.spec.md"
    assert spec.filepath == "docs/Auth.spec.md"
    assert spec.content == "# Auth\n\nRules.\n"
    assert isinstance(spec, Spec)


def test_build_spec_normalizes_backslashes(analyser: SpecAnalyser) -> None:
    spec = analyser.build_spec(filepath="docs\\Auth.spec.md", content="x")
    assert spec.filepath == "docs/Auth.spec.md"


def test_build_spec_generates_distinct_ids(analyser: SpecAnalyser) -> None:
    a = analyser.build_spec(filepath="a.spec.md", content="1")
    b = analyser.build_spec(filepath="a.spec.md", content="1")
    assert a.id != b.id


def test_build_spec_multiline_unicode_content(analyser: SpecAnalyser) -> None:
    body = "Line1\n\nRésumé — 日本語\n"
    spec = analyser.build_spec(filepath="SPEC.md", content=body)
    assert spec.content == body


def test_build_spec_empty_filepath_raises(analyser: SpecAnalyser) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        analyser.build_spec(filepath="", content="x")


def test_build_spec_strips_slashes(analyser: SpecAnalyser) -> None:
    spec = analyser.build_spec(filepath="/docs/x.spec.md/", content="y")
    assert spec.filepath == "docs/x.spec.md"
