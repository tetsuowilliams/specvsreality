"""Tests for ``ClaimGate``."""

from __future__ import annotations

from unittest.mock import MagicMock

from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_worker.evaluation import CandidateFilter, ClaimGate
from specvsreality_worker.ingestion_config import EvaluationConfig, SpecPatternConfig


def _config() -> EvaluationConfig:
    return EvaluationConfig(
        model_version="m1",
        prompt_version="p1",
        prompt="judge",
        spec_pattern=SpecPatternConfig(),
    )


def _rv(*, path_globs: list[str] | None = None) -> RequirementVersion:
    return RequirementVersion(
        id=99,
        requirement_id=1,
        spec_version_id=1,
        content="x",
        content_hash="0" * 40,
        extraction_model="m",
        extraction_prompt="p",
        path_globs=list(path_globs or []),
    )


def test_skips_when_claim_already_exists() -> None:
    claim_repo = MagicMock()
    claim_repo.has_claim.return_value = True
    candidate_filter = MagicMock(spec=CandidateFilter)

    gate = ClaimGate(
        claim_repo=claim_repo,
        candidate_filter=candidate_filter,
        config=_config(),
    )
    assert (
        gate.needs_evaluation(requirement_version=_rv(), blob_sha="a" * 40) is False
    )
    candidate_filter.is_candidate.assert_not_called()


def test_consults_filter_when_no_existing_claim() -> None:
    claim_repo = MagicMock()
    claim_repo.has_claim.return_value = False
    candidate_filter = MagicMock(spec=CandidateFilter)
    candidate_filter.is_candidate.return_value = True

    gate = ClaimGate(
        claim_repo=claim_repo,
        candidate_filter=candidate_filter,
        config=_config(),
    )
    assert gate.needs_evaluation(
        requirement_version=_rv(),
        blob_sha="b" * 40,
        blob_size_bytes=100,
        path_hint="src/x.py",
    )

    candidate_filter.is_candidate.assert_called_once()


def test_returns_false_when_filter_rejects() -> None:
    claim_repo = MagicMock()
    claim_repo.has_claim.return_value = False
    candidate_filter = MagicMock(spec=CandidateFilter)
    candidate_filter.is_candidate.return_value = False

    gate = ClaimGate(
        claim_repo=claim_repo,
        candidate_filter=candidate_filter,
        config=_config(),
    )
    assert (
        gate.needs_evaluation(requirement_version=_rv(), blob_sha="c" * 40) is False
    )


def test_candidate_filter_rejects_huge_blob() -> None:
    candidate_filter = CandidateFilter(max_bytes=50)
    assert (
        candidate_filter.is_candidate(
            blob_size_bytes=1000,
            path_hint="src/big.txt",
            requirement_version=_rv(),
        )
        is False
    )


def test_candidate_filter_rejects_known_binary() -> None:
    candidate_filter = CandidateFilter()
    assert (
        candidate_filter.is_candidate(
            blob_size_bytes=10,
            path_hint="assets/logo.png",
            requirement_version=_rv(),
        )
        is False
    )


def test_candidate_filter_accepts_path_matching_requirement_glob() -> None:
    candidate_filter = CandidateFilter()
    assert (
        candidate_filter.is_candidate(
            blob_size_bytes=10,
            path_hint="src/foo/bar.py",
            requirement_version=_rv(path_globs=["src/**/*.py"]),
        )
        is True
    )


def test_candidate_filter_rejects_path_outside_requirement_globs() -> None:
    candidate_filter = CandidateFilter()
    assert (
        candidate_filter.is_candidate(
            blob_size_bytes=10,
            path_hint="docs/readme.md",
            requirement_version=_rv(path_globs=["src/**/*.py", "tests/**/*"]),
        )
        is False
    )


def test_candidate_filter_with_no_globs_treats_path_as_unconstrained() -> None:
    candidate_filter = CandidateFilter()
    assert (
        candidate_filter.is_candidate(
            blob_size_bytes=10,
            path_hint="any/where.txt",
            requirement_version=_rv(path_globs=[]),
        )
        is True
    )


def test_candidate_filter_accepts_any_glob_alternative() -> None:
    candidate_filter = CandidateFilter()
    rv = _rv(path_globs=["src/**/*.py", "frontend/src/**"])
    assert candidate_filter.is_candidate(
        blob_size_bytes=10,
        path_hint="frontend/src/component.tsx",
        requirement_version=rv,
    ) is True
    assert candidate_filter.is_candidate(
        blob_size_bytes=10,
        path_hint="src/x/y/z.py",
        requirement_version=rv,
    ) is True


def test_candidate_filter_without_path_requires_no_globs() -> None:
    candidate_filter = CandidateFilter()
    assert candidate_filter.is_candidate(
        blob_size_bytes=10,
        path_hint=None,
        requirement_version=_rv(path_globs=[]),
    ) is True
    assert candidate_filter.is_candidate(
        blob_size_bytes=10,
        path_hint=None,
        requirement_version=_rv(path_globs=["src/**/*.py"]),
    ) is False
