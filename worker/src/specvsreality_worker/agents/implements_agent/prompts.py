"""Prompt templates for requirement implementation evaluation."""

from __future__ import annotations

SYSTEM_PROMPT = (
    "You are a senior engineer reviewing whether a repository implements a single "
    "functional requirement. "
    "You are given spec-kit markdown (spec, tasks, plan) for background only; the "
    "authoritative statement of the requirement is the requirement text provided "
    "separately. "
    "Use the repository tools to explore the codebase: locate relevant files, read "
    "implementations, and search for symbols or behaviour. "
    "Prefer find_files and read_file over search_text. "
    "When using read_file, request at most ~120 lines per call (start_line/end_line). "
    "When using search_text, always pass a specific file_glob (e.g. src/**/*.py); "
    "never search the whole repository without file_glob. "
    "Start from path_globs hints when provided. "
    "Base your judgment only on code you inspect with the tools. "
    "If critical behaviour is clearly delegated to code you cannot find, set "
    "implemented to false or lower confidence and explain in gaps. "
    "Do not invent file contents, APIs, or evidence. "
    "When finished, return a RequirementJustification with concrete evidence entries "
    "that cite real files and snippets you found."
)


def build_evaluation_prompt(
    *,
    requirement_id: str | None,
    requirement_text: str,
    path_globs: list[str] | None,
    spec_md: str,
    tasks_md: str | None,
    plan_md: str | None,
) -> str:
    req_header = (
        f"Requirement ID: {requirement_id}\n" if requirement_id else "Requirement ID: (none)\n"
    )
    if path_globs:
        globs_block = "Discovery path_globs (search and read within these first):\n" + "\n".join(
            f"- {glob}" for glob in path_globs
        )
    else:
        globs_block = (
            "Discovery path_globs: (none — use find_files with targeted globs before "
            "search_text.)"
        )
    return (
        f"{req_header}"
        "Requirement under review:\n"
        f"{requirement_text}\n\n"
        f"{globs_block}\n\n"
        "Background spec-kit markdown (for context only; do not treat as the requirement):\n\n"
        "<spec.md>\n"
        f"{spec_md}\n"
        "</spec.md>\n\n"
        "<tasks.md>\n"
        f"{tasks_md or ''}\n"
        "</tasks.md>\n\n"
        "<plan.md>\n"
        f"{plan_md or ''}\n"
        "</plan.md>\n\n"
        "Explore the repository using the available tools, then decide whether the "
        "requirement is implemented."
    )
