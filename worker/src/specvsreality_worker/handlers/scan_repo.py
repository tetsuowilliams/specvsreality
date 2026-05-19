"""Handler for ``ScanRepoMessage``: clones a repo and ingests its history."""

from __future__ import annotations

import logging
import os
import shutil
from collections.abc import Callable
from pathlib import Path
from typing import ClassVar
from urllib.parse import quote, urlsplit, urlunsplit

from git import Repo
from git.exc import GitCommandError
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from specvsreality_messages import SCAN_REPO_MESSAGE_TYPE, ScanRepoMessage
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
)
from specvsreality_worker.agents.implements_agent import (
    create_implements_evaluation_agent,
)
from specvsreality_worker.agents.spec_extraction_agent import (
    create_spec_extraction_agent,
)
from specvsreality_worker.domain import CommitRecord
from specvsreality_worker.evaluation import (
    CandidateFilter,
    ClaimGate,
    ImplementationEvaluator,
    RequirementContextResolver,
    RetroactiveBackfillService,
)
from specvsreality_worker.git import GitClient, GitClientError
from specvsreality_worker.handlers.protocol import MessageHandler
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

logger = logging.getLogger(__name__)


IngestionServiceFactory = Callable[[Session, GitClient], IngestionService]


_EXTRACTION_PROMPT = (
    "Extract structured requirements from the spec triplet. Each requirement "
    "must have a stable id and canonical text."
)
_EVALUATION_PROMPT = (
    "Judge whether the supplied source materially implements the requirement."
)


def _build_ingestion_service(
    session: Session, git_client: GitClient
) -> IngestionService:
    """Compose the full ingestion graph for one scan job.

    Repos and pipeline classes are reconstructed per scan because each scan
    runs against a single ``Session`` -- mirrors the prior ``_build_spec_merge``
    pattern that the legacy handler used.
    """
    spec_pattern = SpecPatternConfig()
    extraction_model = os.getenv("SPEC_EXTRACTION_MODEL", "openai:gpt-4o-mini")
    extraction_prompt_version = os.getenv(
        "SPEC_EXTRACTION_PROMPT_VERSION", "v1"
    )
    evaluation_model = os.getenv("IMPLEMENTS_AGENT_MODEL", "openai:gpt-4o-mini")
    evaluation_prompt_version = os.getenv("IMPLEMENTS_PROMPT_VERSION", "v1")

    extraction_config = ExtractionConfig(
        extraction_model=extraction_model,
        extraction_prompt=_EXTRACTION_PROMPT,
        extraction_prompt_version=extraction_prompt_version,
    )
    evaluation_config = EvaluationConfig(
        model_version=evaluation_model,
        prompt_version=evaluation_prompt_version,
        prompt=_EVALUATION_PROMPT,
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
        spec_extraction_agent=create_spec_extraction_agent(),
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
        implements_evaluation_agent=create_implements_evaluation_agent(),
        blob_reader=blob_reader,
        claim_repo=claim_repo,
        config=evaluation_config,
    )
    requirement_context_resolver = RequirementContextResolver(
        spec_repo=spec_repo,
        spec_version_repo=spec_version_repo,
        requirement_version_repo=requirement_version_repo,
    )

    commit_processor = CommitProcessor(
        git_client=git_client,
        commit_repo=commit_repo,
        blob_repo=blob_repo,
        commit_file_repo=commit_file_repo,
    )
    spec_sync_step = SpecSyncStep(
        spec_detector=spec_detector,
        spec_repo=spec_repo,
        spec_version_resolver=spec_version_resolver,
        requirement_extractor=requirement_extractor,
    )
    evaluation_step = EvaluationStep(
        requirement_context_resolver=requirement_context_resolver,
        commit_file_repo=commit_file_repo,
        claim_gate=claim_gate,
        implementation_evaluator=implementation_evaluator,
        config=evaluation_config,
    )
    retroactive_backfill = RetroactiveBackfillService(
        blob_repo=blob_repo,
        claim_gate=claim_gate,
        implementation_evaluator=implementation_evaluator,
    )

    return IngestionService(
        git_client=git_client,
        repository_repo=repository_repo,
        commit_processor=commit_processor,
        spec_sync_step=spec_sync_step,
        evaluation_step=evaluation_step,
        retroactive_backfill_service=retroactive_backfill,
    )


def _sync_database_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql+psycopg2://"):
        return url.replace("postgresql+psycopg2://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def _clone_url_with_optional_token(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    if parsed.scheme != "https":
        return raw_url
    if parsed.username is not None:
        return raw_url

    token = os.getenv("GIT_CLONE_TOKEN", "").strip()
    if not token:
        return raw_url

    username = os.getenv("GIT_CLONE_USERNAME", "x-access-token").strip() or "x-access-token"
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port is not None else ""
    netloc = f"{quote(username)}:{quote(token, safe='')}@{host}{port}"
    return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))


class ScanRepoHandler(MessageHandler):
    """Clones a tracked repository and runs the temporal ingestion pipeline.

    Fully replaces the legacy ``SpecMerge`` / ``ArtifactMerge`` flow:

    * full re-clone into ``REPO_CLONE_ROOT/<repository_id>``
    * walk every commit oldest-first via :class:`IngestionService`
    * cursor advances per commit (last fully ingested SHA)
    """

    message_type: ClassVar[str] = SCAN_REPO_MESSAGE_TYPE

    def __init__(
        self,
        clone_root: str | Path | None = None,
        *,
        ingestion_service_factory: IngestionServiceFactory = _build_ingestion_service,
    ) -> None:
        self._clone_root = Path(
            clone_root or os.getenv("REPO_CLONE_ROOT", "/repos")
        ).resolve()
        self._clone_root.mkdir(parents=True, exist_ok=True)
        if ingestion_service_factory is None:
            raise ValueError("ingestion_service_factory must not be None")
        self._ingestion_service_factory = ingestion_service_factory

    def handle(self, message: BaseModel) -> None:
        if not isinstance(message, ScanRepoMessage):
            raise TypeError(f"expected ScanRepoMessage, got {type(message).__name__}")

        database_url = _sync_database_url(os.environ["DATABASE_URL"])
        engine = create_engine(database_url, future=True)
        session = Session(bind=engine)
        try:
            repository_id = int(message.repo_id)
            repository = RepositoryRepo(session).get_by_id(repository_id)
            if repository is None:
                raise RuntimeError(
                    f"repository row not found: id={repository_id}"
                )

            target_dir = self._clone_root / str(repository.id)
            if target_dir.exists():
                shutil.rmtree(target_dir)

            clone_url = _clone_url_with_optional_token(repository.url)
            try:
                Repo.clone_from(
                    clone_url,
                    str(target_dir),
                    env={"GIT_TERMINAL_PROMPT": "0"},
                )
            except GitCommandError as exc:
                msg = (
                    f"failed to clone repository_id={repository.id} "
                    f"url={repository.url!r}; if this repository is private, "
                    "set GIT_CLONE_TOKEN"
                )
                raise RuntimeError(msg) from exc

            repository.clone_location = str(target_dir)

            try:
                git_client = GitClient(
                    repo_path=target_dir, repository_id=repository.id
                )
            except GitClientError as exc:
                raise RuntimeError(
                    f"failed to read cloned repo at {target_dir}"
                ) from exc

            session.commit()
            logger.info(
                "scan_repo repository_id=%s clone_location=%s",
                repository.id,
                repository.clone_location,
            )

            service = self._ingestion_service_factory(session, git_client)

            def after_commit(commit: CommitRecord) -> None:
                session.refresh(repository)
                repository.cursor_position = commit.sha
                session.commit()
                logger.debug(
                    "scan_repo repository_id=%s cursor=%s",
                    repository.id,
                    commit.sha[:7],
                )

            service.ingest_repo(repository=repository, after_commit=after_commit)

            logger.info(
                "scan_repo done repository_id=%s cursor=%s",
                repository.id,
                (repository.cursor_position or "")[:7],
            )
        finally:
            session.close()
            engine.dispose()
