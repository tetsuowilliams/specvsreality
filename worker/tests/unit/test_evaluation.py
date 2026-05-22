"""Unit tests for evaluation persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from specvsreality_worker.agents.implements_agent.models import CodeEvidence, RequirementJustification
from specvsreality_worker.agents.implements_agent.tool_cache import CommitToolCache
from specvsreality_worker.core.commit_context import CommitContext
from specvsreality_worker.core.evaluation import Evaluation


def test_persist_justification_updates_implementation_at_commit_and_implements() -> None:
    requirement_version = MagicMock()
    requirement_version.id = 10
    requirement_version.requirement_id = 5
    requirement_version.requirement_text = "Must greet users"

    requirement = MagicMock()
    requirement.spec_id = 3
    requirement.paper_id = "FR-1"

    spec_version = MagicMock()
    spec_version.spec_md = "# Spec"
    spec_version.tasks_md = None
    spec_version.plan_md = None

    justification = RequirementJustification(
        requirement="Must greet users",
        implemented=True,
        confidence="high",
        summary="Greeting implemented.",
        evidence=[
            CodeEvidence(
                file="src/main.py",
                line_number=1,
                snippet="def hello(): pass",
                relevance="Provides greeting.",
            ),
        ],
        gaps=[],
    )

    artifact_version = MagicMock()
    artifact_version.id = 99

    implementation_at_commit = MagicMock()
    implementation_at_commit.id = 55

    requirement_version_repo = MagicMock()
    requirement_version_repo.get_versions_at_commit.return_value = [requirement_version]
    requirement_repo = MagicMock()
    requirement_repo.get_by_id.return_value = requirement
    spec_version_repo = MagicMock()
    spec_version_repo.get_for_spec_at_commit.return_value = spec_version
    implements_evaluation_agent = MagicMock()
    implements_evaluation_agent.evaluate.return_value = justification
    implementation_at_commit_repo = MagicMock()
    implementation_at_commit_repo.upsert_evaluation.return_value = implementation_at_commit
    implements_repo = MagicMock()
    artifact_version_repo = MagicMock()
    artifact_version_repo.get_latest_for_artifact_filepath.return_value = artifact_version

    evaluation = Evaluation(
        spec_repo=MagicMock(),
        spec_version_repo=spec_version_repo,
        requirement_repo=requirement_repo,
        requirement_version_repo=requirement_version_repo,
        artifact_version_repo=artifact_version_repo,
        implementation_at_commit_repo=implementation_at_commit_repo,
        implements_repo=implements_repo,
        implements_evaluation_agent=implements_evaluation_agent,
        git_adapter=MagicMock(),
    )

    commit = CommitContext(
        repo_id=1,
        commit_sha="a" * 40,
        commit_datetime=datetime.now(UTC),
    )
    evaluation.evaluate_commit(commit=commit)

    artifact_version_repo.get_latest_for_artifact_filepath.assert_called_once_with(
        filepath="src/main.py",
    )
    implementation_at_commit_repo.upsert_evaluation.assert_called_once_with(
        requirement_version_id=10,
        evaluation_commit_sha="a" * 40,
        implemented=True,
        summary="Greeting implemented.",
        gaps=[],
        confidence="high",
    )
    implements_repo.upsert_evidence.assert_called_once_with(
        implementation_at_commit_id=55,
        artifact_version_id=99,
        evidence_file="src/main.py",
        evidence_line_number=1,
        evidence_snippet="def hello(): pass",
        evidence_relevance="Provides greeting.",
    )


def test_evaluate_commit_passes_shared_tool_cache() -> None:
    requirement_version_a = MagicMock()
    requirement_version_a.id = 10
    requirement_version_a.requirement_id = 5
    requirement_version_a.requirement_text = "Must greet users"
    requirement_version_a.filepath_globs = ["src/**/*.py"]

    requirement_version_b = MagicMock()
    requirement_version_b.id = 11
    requirement_version_b.requirement_id = 6
    requirement_version_b.requirement_text = "Must log out"
    requirement_version_b.filepath_globs = []

    requirement_a = MagicMock()
    requirement_a.spec_id = 3
    requirement_a.paper_id = "FR-1"
    requirement_b = MagicMock()
    requirement_b.spec_id = 3
    requirement_b.paper_id = "FR-2"

    spec_version = MagicMock()
    spec_version.spec_md = "# Spec"
    spec_version.tasks_md = None
    spec_version.plan_md = None

    justification = RequirementJustification(
        requirement="x",
        implemented=True,
        confidence="high",
        summary="ok",
        evidence=[],
        gaps=[],
    )

    requirement_version_repo = MagicMock()
    requirement_version_repo.get_versions_at_commit.return_value = [
        requirement_version_a,
        requirement_version_b,
    ]
    requirement_repo = MagicMock()
    requirement_repo.get_by_id.side_effect = [requirement_a, requirement_b]
    spec_version_repo = MagicMock()
    spec_version_repo.get_for_spec_at_commit.return_value = spec_version
    implements_evaluation_agent = MagicMock()
    implements_evaluation_agent.evaluate.return_value = justification

    evaluation = Evaluation(
        spec_repo=MagicMock(),
        spec_version_repo=spec_version_repo,
        requirement_repo=requirement_repo,
        requirement_version_repo=requirement_version_repo,
        artifact_version_repo=MagicMock(),
        implementation_at_commit_repo=MagicMock(),
        implements_repo=MagicMock(),
        implements_evaluation_agent=implements_evaluation_agent,
        git_adapter=MagicMock(),
    )

    commit = CommitContext(
        repo_id=1,
        commit_sha="a" * 40,
        commit_datetime=datetime.now(UTC),
    )
    evaluation.evaluate_commit(commit=commit)

    assert implements_evaluation_agent.evaluate.call_count == 2
    first_cache = implements_evaluation_agent.evaluate.call_args_list[0].kwargs["tool_cache"]
    second_cache = implements_evaluation_agent.evaluate.call_args_list[1].kwargs["tool_cache"]
    assert isinstance(first_cache, CommitToolCache)
    assert first_cache is second_cache


def test_persist_justification_skips_evidence_when_no_artifact_version() -> None:
    requirement_version = MagicMock()
    requirement_version.id = 10
    requirement_version.requirement_id = 5
    requirement_version.requirement_text = "Must greet users"

    requirement = MagicMock()
    requirement.spec_id = 3
    requirement.paper_id = "FR-1"

    spec_version = MagicMock()
    spec_version.spec_md = "# Spec"
    spec_version.tasks_md = None
    spec_version.plan_md = None

    justification = RequirementJustification(
        requirement="Must greet users",
        implemented=True,
        confidence="high",
        summary="Greeting implemented.",
        evidence=[
            CodeEvidence(
                file="src/main.py",
                line_number=1,
                snippet="def hello(): pass",
                relevance="Provides greeting.",
            ),
        ],
        gaps=[],
    )

    implementation_at_commit = MagicMock()
    implementation_at_commit.id = 55

    requirement_version_repo = MagicMock()
    requirement_version_repo.get_versions_at_commit.return_value = [requirement_version]
    requirement_repo = MagicMock()
    requirement_repo.get_by_id.return_value = requirement
    spec_version_repo = MagicMock()
    spec_version_repo.get_for_spec_at_commit.return_value = spec_version
    implements_evaluation_agent = MagicMock()
    implements_evaluation_agent.evaluate.return_value = justification
    implementation_at_commit_repo = MagicMock()
    implementation_at_commit_repo.upsert_evaluation.return_value = implementation_at_commit
    implements_repo = MagicMock()
    artifact_version_repo = MagicMock()
    artifact_version_repo.get_latest_for_artifact_filepath.return_value = None

    evaluation = Evaluation(
        spec_repo=MagicMock(),
        spec_version_repo=spec_version_repo,
        requirement_repo=requirement_repo,
        requirement_version_repo=requirement_version_repo,
        artifact_version_repo=artifact_version_repo,
        implementation_at_commit_repo=implementation_at_commit_repo,
        implements_repo=implements_repo,
        implements_evaluation_agent=implements_evaluation_agent,
        git_adapter=MagicMock(),
    )

    commit = CommitContext(
        repo_id=1,
        commit_sha="a" * 40,
        commit_datetime=datetime.now(UTC),
    )
    evaluation.evaluate_commit(commit=commit)

    implementation_at_commit_repo.upsert_evaluation.assert_called_once()
    implements_repo.upsert_evidence.assert_not_called()
