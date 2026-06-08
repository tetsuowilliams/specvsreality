"""Dependency injection context for snapshot-scoped agent tools."""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from specvsreality_worker.agents.artifact_candidate_agent.tool_cache import CommitToolCache
    from specvsreality_worker.config import WorkerSettings
    from specvsreality_worker.git_adapter import GitAdapter


@dataclass(frozen=True)
class CommitToolDeps:
    git_adapter: GitAdapter
    commit_sha: str
    settings: WorkerSettings
    label: str | None = None
    path_globs: tuple[str, ...] = ()
    tool_cache: CommitToolCache | None = None
    # Serialize git subprocesses when Pydantic AI runs multiple tools in parallel.
    git_lock: threading.Lock = field(default_factory=threading.Lock, compare=False, hash=False)
