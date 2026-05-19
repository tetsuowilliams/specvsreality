"""End-to-end ingestion against a real fixture git repo and Postgres database.

Wires :class:`IngestionService` with the real production graph except for the
two LLM agents, which are replaced by deterministic in-memory fakes. The point
of this test is to exercise the temporal schema as a whole -- the seams between
``CommitProcessor``, ``SpecSyncStep``, ``EvaluationStep``, and the repository
package -- not to validate any one component.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from fixtures.git_repos import (
    add_commit,
    init_repo_with_config,
    rename_default_branch_to_main,
)
from specvsreality_repositories.models.commit import Commit
from specvsreality_repositories.models.commit_file import CommitFile
from specvsreality_repositories.models.implementation_claim import ImplementationClaim
from specvsreality_repositories.models.requirement import Requirement
from specvsreality_repositories.models.requirement_version import RequirementVersion
from specvsreality_repositories.models.spec import Spec
from specvsreality_repositories.models.spec_version import SpecVersion
from specvsreality_repositories.repos import (
    BlobRepo,
    CommitFileRepo,
    CommitRepo,
    ImplementationClaimRepo,
    RepositoryRepo,
    RequirementRepo,
    RequirementVersionRepo,
    SpecRepo,
    SpecVersionRepo,
    Verdict,
)
from specvsreality_worker.agents.implements_agent.models import ImplementsAssessment
from specvsreality_worker.agents.spec_extraction_agent.models import (
    ParsedRequirement,
    SpecExtractionResult,
)
from specvsreality_worker.evaluation import (
    CandidateFilter,
    ClaimGate,
    ImplementationEvaluator,
    RequirementContextResolver,
    RetroactiveBackfillService,
)
from specvsreality_worker.git import GitClient
from specvsreality_worker.ingestion import (
    CommitProcessor,
    EvaluationStep,
    IngestionService,
    SpecSyncStep,
)
from specvsreality_worker.ingestion_config import (
    EvaluationConfig,
    ExtractionConfig,
    SpecPatternConfig,
)
from specvsreality_worker.spec import (
    RequirementExtractor,
    RequirementVersionWriter,
    SpecDetector,
    SpecVersionResolver,
)
from specvsreality_worker.support import BlobReader, HashUtil

_SPEC_BODY = """# Foo Spec

## Functional requirements

- FR-001: The system must greet the user.
- FR-002: The system must log greetings.
"""

_PLAN_BODY = "# Plan\n\nImplement FR-001 in src/foo.py.\n"
_TASKS_BODY = "# Tasks\n\n- T1: Greet\n- T2: Log\n"

_FOO_SOURCE = """def greet(name: str) -> str:
    \"\"\"Implements FR-001 by greeting the user.\"\"\"
    return f"hello {name}"
"""

_LOGGER_SOURCE = """import logging

def log_greeting(message: str) -> None:
    \"\"\"Implements FR-002 by logging the greeting.\"\"\"
    logging.getLogger(__name__).info(message)
"""


class _FakeSpecExtractionAgent:
    """Returns a fixed two-requirement extraction result for any spec text."""

    def __init__(self) -> None:
        self.calls = 0

    def extract_spec(
        self, *, spec_md: str, tasks_md: str | None, plan_md: str | None
    ) -> SpecExtractionResult:
        del spec_md, tasks_md, plan_md
        self.calls += 1
        return SpecExtractionResult(
            spec_title="Foo",
            functional_requirements=[
                ParsedRequirement(
                    id="FR-001",
                    text="System must greet the user.",
                    path_globs=["src/**/*.py"],
                ),
                ParsedRequirement(
                    id="FR-002",
                    text="System must log greetings.",
                    path_globs=["src/**/*.py"],
                ),
            ],
        )


class _FakeImplementsAgent:
    """Pretends FR-001 is implemented by ``foo.py`` and FR-002 by ``logger.py``."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def evaluate(
        self,
        *,
        spec_md: str,
        tasks_md: str | None,
        plan_md: str | None,
        requirement_id: str | None,
        requirement_text: str,
        artifact_sources: list[tuple[str, str]],
    ) -> ImplementsAssessment:
        del spec_md, tasks_md, plan_md, requirement_id
        path, source = artifact_sources[0]
        self.calls.append((requirement_text, path))
        implements = (
            ("greet" in requirement_text.lower() and "greet" in source)
            or ("log" in requirement_text.lower() and "log_greeting" in source)
        )
        return ImplementsAssessment(
            implements=implements,
            confidence="high" if implements else "medium",
            reasoning="fake reasoning",
            gaps=[],
        )


def _build_service(
    *,
    session: Session,
    git_client: GitClient,
    spec_agent: _FakeSpecExtractionAgent,
    impl_agent: _FakeImplementsAgent,
) -> IngestionService:
    spec_pattern = SpecPatternConfig()
    extraction_config = ExtractionConfig(
        extraction_model="test-extract",
        extraction_prompt="extract",
        extraction_prompt_version="v1",
    )
    evaluation_config = EvaluationConfig(
        model_version="test-evaluator",
        prompt_version="v1",
        prompt="evaluate",
        spec_pattern=spec_pattern,
    )

    blob_reader = BlobReader(git_client=git_client)
    hash_util = HashUtil()

    repository_repo = RepositoryRepo(session)
    commit_repo = CommitRepo(session)
    blob_repo = BlobRepo(session)
    commit_file_repo = CommitFileRepo(session)
    spec_repo = SpecRepo(session)
    spec_version_repo = SpecVersionRepo(session)
    requirement_repo = RequirementRepo(session)
    requirement_version_repo = RequirementVersionRepo(session)
    claim_repo = ImplementationClaimRepo(session)

    spec_detector = SpecDetector(config=spec_pattern)
    spec_version_resolver = SpecVersionResolver(
        spec_version_repo=spec_version_repo,
        commit_file_repo=commit_file_repo,
    )
    requirement_version_writer = RequirementVersionWriter(
        requirement_repo=requirement_repo,
        requirement_version_repo=requirement_version_repo,
        hash_util=hash_util,
    )
    requirement_extractor = RequirementExtractor(
        spec_extraction_agent=spec_agent,
        blob_reader=blob_reader,
        requirement_version_writer=requirement_version_writer,
        config=extraction_config,
    )
    candidate_filter = CandidateFilter()
    claim_gate = ClaimGate(
        claim_repo=claim_repo,
        candidate_filter=candidate_filter,
        config=evaluation_config,
    )
    implementation_evaluator = ImplementationEvaluator(
        implements_evaluation_agent=impl_agent,
        blob_reader=blob_reader,
        claim_repo=claim_repo,
        config=evaluation_config,
    )
    requirement_context_resolver = RequirementContextResolver(
        spec_repo=spec_repo,
        spec_version_repo=spec_version_repo,
        requirement_version_repo=requirement_version_repo,
    )

    return IngestionService(
        git_client=git_client,
        repository_repo=repository_repo,
        commit_processor=CommitProcessor(
            git_client=git_client,
            commit_repo=commit_repo,
            blob_repo=blob_repo,
            commit_file_repo=commit_file_repo,
        ),
        spec_sync_step=SpecSyncStep(
            spec_detector=spec_detector,
            spec_repo=spec_repo,
            spec_version_resolver=spec_version_resolver,
            requirement_extractor=requirement_extractor,
        ),
        evaluation_step=EvaluationStep(
            requirement_context_resolver=requirement_context_resolver,
            commit_file_repo=commit_file_repo,
            claim_gate=claim_gate,
            implementation_evaluator=implementation_evaluator,
            config=evaluation_config,
        ),
        retroactive_backfill_service=RetroactiveBackfillService(
            blob_repo=blob_repo,
            claim_gate=claim_gate,
            implementation_evaluator=implementation_evaluator,
        ),
    )


def _make_fixture_repo(base: Path) -> tuple[Path, list[str]]:
    """Build a 4-commit history exercising spec, code, and update flows."""
    path = base / "repo"
    path.mkdir()
    repo = init_repo_with_config(path)
    rename_default_branch_to_main(repo)

    shas: list[str] = []
    shas.append(add_commit(repo, "init", {"README.md": "# repo\n"}))
    shas.append(
        add_commit(
            repo,
            "add foo spec",
            {
                "specs/foo/spec.md": _SPEC_BODY,
                "specs/foo/plan.md": _PLAN_BODY,
                "specs/foo/tasks.md": _TASKS_BODY,
            },
        )
    )
    shas.append(add_commit(repo, "implement greet", {"src/foo.py": _FOO_SOURCE}))
    shas.append(
        add_commit(repo, "implement logger", {"src/logger.py": _LOGGER_SOURCE})
    )
    return path, shas


def _commit_count(session: Session, repository_id: int) -> int:
    return (
        session.query(Commit)
        .filter(Commit.repository_id == repository_id)
        .count()
    )


def _filenames_at(session: Session, commit_sha: str) -> set[str]:
    rows: Iterable[CommitFile] = (
        session.query(CommitFile).filter(CommitFile.commit_sha == commit_sha).all()
    )
    return {r.path for r in rows}


@pytest.mark.usefixtures("engine")
def test_ingest_repo_persists_full_temporal_history(
    tmp_path: Path, db_session: Session
) -> None:
    """End-to-end: commits → spec versions → requirement versions → claims."""
    path, shas = _make_fixture_repo(tmp_path)
    repository = RepositoryRepo(db_session).add(
        name="ingest-e2e",
        url=f"file://{path}",
        clone_location=str(path),
    )
    db_session.flush()

    git_client = GitClient(repo_path=path, repository_id=int(repository.id))
    spec_agent = _FakeSpecExtractionAgent()
    impl_agent = _FakeImplementsAgent()
    service = _build_service(
        session=db_session,
        git_client=git_client,
        spec_agent=spec_agent,
        impl_agent=impl_agent,
    )

    seen: list[str] = []
    service.ingest_repo(
        repository=repository,
        after_commit=lambda c: seen.append(c.sha),
    )

    assert seen == shas, "ingestion should walk all commits oldest-first"

    assert _commit_count(db_session, int(repository.id)) == len(shas)
    assert _filenames_at(db_session, shas[0]) == {"README.md"}
    assert "specs/foo/spec.md" in _filenames_at(db_session, shas[1])
    assert "src/foo.py" in _filenames_at(db_session, shas[2])
    assert "src/logger.py" in _filenames_at(db_session, shas[3])

    specs = (
        db_session.query(Spec).filter(Spec.repository_id == repository.id).all()
    )
    assert [s.name for s in specs] == ["foo"]

    spec_versions = (
        db_session.query(SpecVersion)
        .filter(SpecVersion.spec_id == specs[0].id)
        .all()
    )
    assert len(spec_versions) == 1, "spec triplet was added once and never modified"
    assert spec_versions[0].first_seen_commit == shas[1]

    assert spec_agent.calls == 1, "extractor must run exactly once per new spec version"

    requirements = (
        db_session.query(Requirement)
        .filter(Requirement.spec_id == specs[0].id)
        .order_by(Requirement.external_id)
        .all()
    )
    assert [r.external_id for r in requirements] == ["FR-001", "FR-002"]

    requirement_versions = (
        db_session.query(RequirementVersion)
        .filter(RequirementVersion.spec_version_id == spec_versions[0].id)
        .all()
    )
    assert len(requirement_versions) == 2

    claims = (
        db_session.query(ImplementationClaim)
        .order_by(ImplementationClaim.id)
        .all()
    )
    assert claims, "evaluator should produce claims for source blobs"

    implements_claims = [c for c in claims if c.verdict == Verdict.IMPLEMENTS.value]
    rv_by_external = {
        r.external_id: rv.id
        for r in requirements
        for rv in requirement_versions
        if rv.requirement_id == r.id
    }
    fr001_implements = {
        c.blob_sha
        for c in implements_claims
        if c.requirement_version_id == rv_by_external["FR-001"]
    }
    fr002_implements = {
        c.blob_sha
        for c in implements_claims
        if c.requirement_version_id == rv_by_external["FR-002"]
    }
    assert fr001_implements, "FR-001 should be marked implemented by foo.py"
    assert fr002_implements, "FR-002 should be marked implemented by logger.py"

    rerun_session = db_session
    rerun_service = _build_service(
        session=rerun_session,
        git_client=git_client,
        spec_agent=spec_agent,
        impl_agent=impl_agent,
    )
    pre_rerun_extract_calls = spec_agent.calls
    pre_rerun_eval_calls = len(impl_agent.calls)
    rerun_service.ingest_repo(repository=repository)

    assert spec_agent.calls == pre_rerun_extract_calls, (
        "spec extraction should be skipped on idempotent re-run (same triplet)"
    )
    assert len(impl_agent.calls) == pre_rerun_eval_calls, (
        "ClaimGate should suppress duplicate (rv, blob, model, prompt) evaluations"
    )


def _make_partial_triplet_repo(base: Path) -> tuple[Path, list[str]]:
    """Build a history where ``spec.md`` lands first and plan/tasks arrive later."""
    path = base / "partial-repo"
    path.mkdir()
    repo = init_repo_with_config(path)
    rename_default_branch_to_main(repo)
    shas: list[str] = [
        add_commit(repo, "spec only", {"specs/bar/spec.md": _SPEC_BODY}),
        add_commit(
            repo,
            "add plan + tasks",
            {
                "specs/bar/plan.md": _PLAN_BODY,
                "specs/bar/tasks.md": _TASKS_BODY,
            },
        ),
    ]
    return path, shas


@pytest.mark.usefixtures("engine")
def test_partial_triplet_creates_two_spec_versions(
    tmp_path: Path, db_session: Session
) -> None:
    """spec.md alone is enough for a SpecVersion; adding plan/tasks adds a second."""
    path, shas = _make_partial_triplet_repo(tmp_path)
    repository = RepositoryRepo(db_session).add(
        name="partial-triplet-e2e",
        url=f"file://{path}",
        clone_location=str(path),
    )
    db_session.flush()

    git_client = GitClient(repo_path=path, repository_id=int(repository.id))
    spec_agent = _FakeSpecExtractionAgent()
    impl_agent = _FakeImplementsAgent()
    service = _build_service(
        session=db_session,
        git_client=git_client,
        spec_agent=spec_agent,
        impl_agent=impl_agent,
    )
    service.ingest_repo(repository=repository)

    spec = (
        db_session.query(Spec)
        .filter(Spec.repository_id == repository.id, Spec.name == "bar")
        .one()
    )
    versions = (
        db_session.query(SpecVersion)
        .filter(SpecVersion.spec_id == spec.id)
        .order_by(SpecVersion.first_seen_at)
        .all()
    )

    assert len(versions) == 2, "spec.md only + spec.md+plan+tasks = two distinct triplets"
    assert versions[0].first_seen_commit == shas[0]
    assert versions[0].plan_blob_sha is None
    assert versions[0].tasks_blob_sha is None
    assert versions[1].first_seen_commit == shas[1]
    assert versions[1].plan_blob_sha is not None
    assert versions[1].tasks_blob_sha is not None
    assert spec_agent.calls == 2, "each new spec version triggers one extraction"
