"""Run the ingestion pipeline against a local git checkout, no broker required.

Use this for debugging / breakpoint sessions: it builds the same dependency
graph as :class:`ScanRepoHandler` but does not go through RabbitMQ, so you can
pause inside ``SpecVersionResolver``, ``RequirementExtractor``, etc. without
standing up the queue.

By default it ingests the toy fixture repo at
``https://github.com/tetsuowilliams/spec_test_toy`` against a local Postgres
running at ``localhost:5432``. Both can be overridden via ``--repo-url`` and
``--database-url`` (or the ``DATABASE_URL`` env var).

The first run clones the repo into a cache directory under
``~/.cache/specvsreality/scan-local/<repo-name>``; subsequent runs reuse that
checkout, so the inner loop is "edit worker code, ``--reset``, re-run".

Typical invocation (also wired up in ``.vscode/launch.json``)::

    uv run specvsreality-scan-local --reset --verbose
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
from collections.abc import Sequence
from pathlib import Path
from urllib.parse import urlsplit

from git import Repo
from git.exc import GitCommandError
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import Session

from specvsreality_repositories.models.repository import Repository
from specvsreality_repositories.repos import RepositoryRepo
from specvsreality_worker.domain import CommitRecord
from specvsreality_worker.git import GitClient, GitClientError
from specvsreality_worker.handlers.scan_repo import (
    _build_ingestion_service,
    _sync_database_url,
)
from specvsreality_worker.main import _load_worker_dotenv
from specvsreality_worker.observability import init_worker_observability

logger = logging.getLogger("specvsreality_worker.scripts.scan_local")

DEFAULT_REPO_URL = "https://github.com/tetsuowilliams/spec_test_toy"
DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://specvsreality:specvsreality"
    "@localhost:5432/specvsreality"
)
DEFAULT_CHECKOUT_ROOT = Path.home() / ".cache" / "specvsreality" / "scan-local"


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="specvsreality-scan-local",
        description=(
            "Run the temporal ingestion pipeline against a local git checkout. "
            "Bypasses RabbitMQ so you can attach a debugger and step through "
            "commit-by-commit."
        ),
    )
    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help=(
            "Git URL to clone if --repo-path is not yet a checkout. "
            f"Default: {DEFAULT_REPO_URL}"
        ),
    )
    parser.add_argument(
        "--repo-path",
        default=None,
        help=(
            "Path to a working git checkout on disk. If absent, the repo is "
            f"cloned into {DEFAULT_CHECKOUT_ROOT}/<repo-name>. The checkout is "
            "reused across runs."
        ),
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL,
        help=(
            "SQLAlchemy URL for the target Postgres "
            f"(default: $DATABASE_URL or {DEFAULT_DATABASE_URL}). "
            "postgresql:// / postgresql+asyncpg:// / postgresql+psycopg2:// "
            "are all rewritten to the sync psycopg driver automatically."
        ),
    )
    parser.add_argument(
        "--repo-name",
        default=None,
        help="Repository row 'name' (defaults to the basename of --repo-url).",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Delete the existing repository row (and everything it cascades to: "
            "commits, spec_versions, requirement_versions, claims) before "
            "ingesting. Blobs may remain orphaned -- that is harmless."
        ),
    )
    parser.add_argument(
        "--reclone",
        action="store_true",
        help=(
            "Wipe the local checkout (if any) and reclone from --repo-url "
            "before ingesting. Independent of --reset."
        ),
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Bump worker logging to DEBUG.",
    )
    return parser.parse_args(argv)


def _configure_logging(*, verbose: bool) -> None:
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
        stream=sys.stderr,
    )


def _repo_basename(repo_url: str) -> str:
    """Last URL path segment, with a trailing ``.git`` stripped."""
    last = Path(urlsplit(repo_url).path).name
    return last.removesuffix(".git") or "repo"


def _ensure_checkout(
    *, repo_url: str, repo_path: Path, reclone: bool
) -> Path:
    """Make ``repo_path`` a working checkout of ``repo_url``.

    * if ``--reclone``: nuke and reclone unconditionally
    * if ``repo_path`` already a checkout: reuse it (do NOT auto-pull, the
      operator is in charge of fetching new commits)
    * if ``repo_path`` is missing: clone it
    * if ``repo_path`` exists but isn't a checkout: bail out, never overwrite
      arbitrary directories
    """
    if reclone and repo_path.exists():
        logger.info("--reclone: removing %s", repo_path)
        shutil.rmtree(repo_path)

    if (repo_path / ".git").exists():
        logger.debug("reusing existing checkout at %s", repo_path)
        return repo_path

    if repo_path.exists():
        raise RuntimeError(
            f"{repo_path} exists but is not a git checkout; "
            "delete it manually or pass --repo-path elsewhere"
        )

    logger.info("cloning %s -> %s", repo_url, repo_path)
    repo_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        Repo.clone_from(
            repo_url,
            str(repo_path),
            env={"GIT_TERMINAL_PROMPT": "0"},
        )
    except GitCommandError as exc:
        raise RuntimeError(f"failed to clone {repo_url}: {exc}") from exc
    return repo_path


def _get_or_create_repository(
    *,
    session: Session,
    name: str,
    url: str,
    clone_location: str,
    reset: bool,
) -> Repository:
    repository_repo = RepositoryRepo(session)
    existing = repository_repo.get_by_name(name)
    if existing is not None and reset:
        logger.info(
            "reset: deleting repository_id=%s name=%r and all dependent rows",
            existing.id,
            name,
        )
        session.execute(delete(Repository).where(Repository.id == existing.id))
        session.commit()
        existing = None

    if existing is None:
        return repository_repo.add(
            name=name, url=url, clone_location=clone_location
        )

    existing.clone_location = clone_location
    return existing


def main(argv: Sequence[str] | None = None) -> int:
    # Load worker/.env first so DATABASE_URL / OPENAI_API_KEY from there feed
    # both argparse defaults and the LLM agents.
    _load_worker_dotenv()
    args = _parse_args(argv)
    _configure_logging(verbose=args.verbose)
    init_worker_observability()

    repo_name = args.repo_name or _repo_basename(args.repo_url)
    repo_path = (
        Path(args.repo_path).expanduser().resolve()
        if args.repo_path
        else (DEFAULT_CHECKOUT_ROOT / repo_name).resolve()
    )

    try:
        repo_path = _ensure_checkout(
            repo_url=args.repo_url,
            repo_path=repo_path,
            reclone=args.reclone,
        )
    except RuntimeError as exc:
        logger.error("%s", exc)
        return 2

    engine = create_engine(_sync_database_url(args.database_url), future=True)
    try:
        with Session(engine) as session:
            repository = _get_or_create_repository(
                session=session,
                name=repo_name,
                url=args.repo_url,
                clone_location=str(repo_path),
                reset=args.reset,
            )
            session.commit()

            try:
                git_client = GitClient(
                    repo_path=repo_path, repository_id=int(repository.id)
                )
            except GitClientError as exc:
                logger.error("failed to read git repo at %s: %s", repo_path, exc)
                return 1

            service = _build_ingestion_service(session, git_client)

            def after_commit(commit: CommitRecord) -> None:
                """Match ``ScanRepoHandler``: advance cursor per commit."""
                session.refresh(repository)
                repository.cursor_position = commit.sha
                session.commit()
                logger.debug(
                    "commit done sha=%s message=%r",
                    commit.sha[:7],
                    (commit.message or "").splitlines()[0] if commit.message else "",
                )

            logger.info(
                "ingest start repository_id=%s name=%r url=%s path=%s",
                repository.id,
                repository.name,
                repository.url,
                repo_path,
            )
            service.ingest_repo(
                repository=repository, after_commit=after_commit
            )
            logger.info(
                "ingest done repository_id=%s cursor=%s",
                repository.id,
                (repository.cursor_position or "")[:7],
            )
    finally:
        engine.dispose()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
