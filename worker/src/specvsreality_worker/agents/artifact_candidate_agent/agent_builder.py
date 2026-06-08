"""Construct the Pydantic AI agent with snapshot-scoped repository tools."""

from __future__ import annotations

from pydantic_ai import Agent, RunContext

from specvsreality_worker.agents.artifact_candidate_agent.deps import CommitToolDeps
from specvsreality_worker.agents.artifact_candidate_agent.models import ArtifactCandidateResult
from specvsreality_worker.agents.artifact_candidate_agent.prompts import SYSTEM_PROMPT
from specvsreality_worker.agents.artifact_candidate_agent.repository_tools import (
    find_files,
    list_directory,
    read_file,
    search_text,
)
from specvsreality_worker.config import WorkerSettings


def build_artifact_candidate_agent(
    settings: WorkerSettings,
) -> Agent[CommitToolDeps, ArtifactCandidateResult]:
    agent: Agent[CommitToolDeps, ArtifactCandidateResult] = Agent(
        model=settings.artifact_candidate_agent_model,
        deps_type=CommitToolDeps,
        output_type=ArtifactCandidateResult,
        system_prompt=SYSTEM_PROMPT,
    )

    @agent.tool
    def find_files_tool(ctx: RunContext[CommitToolDeps], glob: str) -> list[str]:
        """Find tracked files matching a glob pattern (e.g. src/**/*.py)."""
        return find_files(ctx.deps, glob)

    @agent.tool
    def list_directory_tool(ctx: RunContext[CommitToolDeps], path: str) -> list[str]:
        """List immediate children under a directory path."""
        return list_directory(ctx.deps, path)

    @agent.tool
    def read_file_tool(
        ctx: RunContext[CommitToolDeps],
        path: str,
        start_line: int | None = None,
        end_line: int | None = None,
    ) -> str:
        """Read a UTF-8 file, optionally limited to a 1-based line range (~120 lines max)."""
        return read_file(ctx.deps, path, start_line=start_line, end_line=end_line)

    @agent.tool
    def search_text_tool(
        ctx: RunContext[CommitToolDeps],
        pattern: str,
        path: str = ".",
        file_glob: str | None = None,
    ) -> list[str]:
        """Search tracked files for a regex pattern.

        Always set ``file_glob`` (e.g. ``src/**/*.py``) when ``path`` is ``.`` or empty.
        Prefer ``find_files`` + ``read_file`` over wide searches.
        """
        return search_text(ctx.deps, pattern, path=path, file_glob=file_glob)

    return agent
