"""Environment-backed limits for the implements evaluation agent."""

from __future__ import annotations

import os

from pydantic_ai.usage import UsageLimits


def _int_env(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    return int(raw)


def implements_agent_timeout_seconds() -> float:
    """Wall-clock cap for a single requirement evaluation (``run_sync``)."""
    raw = os.environ.get("IMPLEMENTS_AGENT_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return 600.0
    return float(raw)


def implements_agent_usage_limits() -> UsageLimits:
    """Model request and tool-call caps per evaluation run."""
    return UsageLimits(
        request_limit=_int_env("IMPLEMENTS_AGENT_REQUEST_LIMIT", 30),
        tool_calls_limit=_int_env("IMPLEMENTS_AGENT_TOOL_CALLS_LIMIT", 40),
    )


def search_text_max_files() -> int:
    """Maximum tracked files to read per ``search_text`` call."""
    return _int_env("IMPLEMENTS_AGENT_SEARCH_MAX_FILES", 60)


def search_text_max_matches() -> int:
    """Maximum match lines returned from one ``search_text`` call."""
    return _int_env("IMPLEMENTS_AGENT_SEARCH_MAX_MATCHES", 50)


def find_files_max_results() -> int:
    """Maximum paths returned from one ``find_files`` call."""
    return _int_env("IMPLEMENTS_AGENT_FIND_FILES_MAX", 200)


def tool_timeout_seconds() -> float:
    """Wall-clock cap for a single repository tool invocation."""
    raw = os.environ.get("IMPLEMENTS_AGENT_TOOL_TIMEOUT_SECONDS", "").strip()
    if not raw:
        return 90.0
    return float(raw)


def read_file_max_bytes() -> int:
    """Refuse to load whole files larger than this (bytes)."""
    return _int_env("IMPLEMENTS_AGENT_READ_MAX_BYTES", 256_000)


def read_file_max_lines() -> int:
    """When reading a full file, return at most this many lines."""
    return _int_env("IMPLEMENTS_AGENT_READ_MAX_LINES", 400)


def read_file_max_line_span() -> int:
    """Maximum inclusive line span per ``read_file`` call (``end_line - start_line + 1``)."""
    return _int_env("IMPLEMENTS_AGENT_READ_MAX_LINE_SPAN", 120)
