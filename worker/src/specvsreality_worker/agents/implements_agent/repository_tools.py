"""Repository exploration tools scoped to a single snapshot."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from typing import TypeVar

from specvsreality_worker.agents.implements_agent.deps import CommitToolDeps
from specvsreality_worker.agents.implements_agent.glob import (
    files_under_prefix,
    glob_match,
    normalize_relpath,
)
from specvsreality_worker.agents.implements_agent.settings import (
    find_files_max_results,
    read_file_max_bytes,
    read_file_max_line_span,
    read_file_max_lines,
    search_text_max_files,
    search_text_max_matches,
)

logger = logging.getLogger(__name__)

_BLOCKED_SUFFIXES = frozenset(
    {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".webp",
        ".zip",
        ".gz",
        ".tar",
        ".pyc",
        ".woff",
        ".woff2",
        ".ico",
        ".mp4",
        ".mp3",
    },
)

T = TypeVar("T")


def _req_label(deps: CommitToolDeps) -> str:
    return deps.requirement_id or "?"


def _is_blocked_path(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(suffix) for suffix in _BLOCKED_SUFFIXES)


def _execute_tool(
    deps: CommitToolDeps,
    tool_name: str,
    detail: str,
    fn: Callable[[], T],
) -> T:
    """Run a repository tool; git access is serialized via ``deps.git_lock``."""
    logger.info(
        "tool %s start requirement_id=%s commit=%s %s",
        tool_name,
        _req_label(deps),
        deps.commit_sha[:7],
        detail,
    )
    started = time.monotonic()
    with deps.git_lock:
        result = fn()
    elapsed_s = time.monotonic() - started
    if elapsed_s > 5.0:
        logger.warning(
            "tool %s slow requirement_id=%s commit=%s elapsed_s=%.2f %s",
            tool_name,
            _req_label(deps),
            deps.commit_sha[:7],
            elapsed_s,
            detail,
        )
    return result


def _run_cached_tool(
    deps: CommitToolDeps,
    tool_name: str,
    cache_key: tuple[object, ...],
    detail: str,
    fn: Callable[[], T],
) -> T:
    """Run a tool, reusing a prior result from ``deps.tool_cache`` when present."""
    cache = deps.tool_cache
    if cache is not None and cache.has(cache_key):
        logger.info(
            "tool %s cache_hit requirement_id=%s commit=%s %s",
            tool_name,
            _req_label(deps),
            deps.commit_sha[:7],
            detail,
        )
        return cache.get(cache_key)

    result = _execute_tool(deps, tool_name, detail, fn)
    if cache is not None:
        cache.put(cache_key, result)
    return result


def find_files(deps: CommitToolDeps, glob: str) -> list[str]:
    """Return tracked file paths matching ``glob``."""
    pattern = glob.strip()
    if not pattern:
        return []

    def _run() -> list[str]:
        started = time.monotonic()
        matches: list[str] = []
        for path in deps.git_adapter.list_files_at_commit(deps.commit_sha):
            if glob_match(pattern, path):
                matches.append(path)

        cap = find_files_max_results()
        truncated = len(matches) > cap
        if truncated:
            matches = matches[:cap]

        logger.info(
            "tool find_files done requirement_id=%s commit=%s glob=%r matches=%s "
            "truncated=%s elapsed_s=%.2f",
            _req_label(deps),
            deps.commit_sha[:7],
            pattern,
            len(matches),
            truncated,
            time.monotonic() - started,
        )
        if truncated:
            matches.append(
                f"warning: truncated to {cap} paths; use a narrower glob.",
            )
        return matches

    return _run_cached_tool(
        deps,
        "find_files",
        ("find_files", pattern),
        f"glob={pattern!r}",
        _run,
    )


def list_directory(deps: CommitToolDeps, path: str) -> list[str]:
    """Return immediate children under ``path`` in the repository tree."""
    from specvsreality_worker.git_adapter import GitAdapterError

    def _run() -> list[str]:
        started = time.monotonic()
        try:
            children = deps.git_adapter.list_directory_at_commit(deps.commit_sha, path)
        except GitAdapterError as exc:
            return [f"error: {exc}"]
        logger.info(
            "tool list_directory done requirement_id=%s commit=%s path=%r children=%s "
            "elapsed_s=%.2f",
            _req_label(deps),
            deps.commit_sha[:7],
            path,
            len(children),
            time.monotonic() - started,
        )
        return children

    return _run_cached_tool(
        deps,
        "list_directory",
        ("list_directory", path),
        f"path={path!r}",
        _run,
    )


def read_file(
    deps: CommitToolDeps,
    path: str,
    start_line: int | None = None,
    end_line: int | None = None,
) -> str:
    """Return file contents, optionally limited to a 1-based inclusive line range."""
    from specvsreality_worker.git_adapter import GitAdapterError

    if _is_blocked_path(path):
        return (
            f"error: refusing to read {path!r} (binary or non-text file type); "
            "inspect a smaller text source file instead."
        )

    line_range = start_line is not None or end_line is not None
    detail = f"path={path!r}" + (
        f" lines={start_line}-{end_line}" if line_range else " full_file"
    )

    def _run() -> str:
        started = time.monotonic()
        max_bytes = read_file_max_bytes()
        try:
            size = deps.git_adapter.blob_size_at_commit(deps.commit_sha, path)
        except GitAdapterError as exc:
            return f"error: {exc}"

        if line_range:
            start = max(1, start_line or 1)
            end = max(start, end_line or start)
            span = end - start + 1
            max_span = read_file_max_line_span()
            if span > max_span:
                return (
                    f"error: line range {start}-{end} spans {span} lines "
                    f"(limit {max_span}); read in smaller chunks."
                )
            try:
                selected = deps.git_adapter.file_lines_at_commit(
                    deps.commit_sha,
                    path,
                    start_line=start,
                    end_line=end,
                )
            except GitAdapterError as exc:
                return f"error: {exc}"
            logger.info(
                "tool read_file done requirement_id=%s commit=%s path=%r bytes=%s "
                "lines=%s-%s streamed=True elapsed_s=%.2f",
                _req_label(deps),
                deps.commit_sha[:7],
                path,
                size,
                start,
                end,
                time.monotonic() - started,
            )
            if not selected:
                return ""
            return "\n".join(
                f"{index}: {line}" for index, line in enumerate(selected, start=start)
            )

        if size > max_bytes:
            return (
                f"error: file {path!r} is {size} bytes (limit {max_bytes}); "
                "call read_file with start_line and end_line to read a smaller slice."
            )

        try:
            content = deps.git_adapter.file_at_commit(deps.commit_sha, path)
        except GitAdapterError as exc:
            return f"error: {exc}"

        lines = content.splitlines()
        if not lines:
            logger.info(
                "tool read_file done requirement_id=%s commit=%s path=%r empty elapsed_s=%.2f",
                _req_label(deps),
                deps.commit_sha[:7],
                path,
                time.monotonic() - started,
            )
            return ""

        max_lines = read_file_max_lines()
        if len(lines) > max_lines:
            lines = lines[:max_lines]
            body = "\n".join(
                f"{index}: {line}" for index, line in enumerate(lines, start=1)
            )
            logger.info(
                "tool read_file done requirement_id=%s commit=%s path=%r bytes=%s "
                "truncated_lines=True elapsed_s=%.2f",
                _req_label(deps),
                deps.commit_sha[:7],
                path,
                size,
                time.monotonic() - started,
            )
            return (
                f"{body}\n\nwarning: file has more than {max_lines} lines; "
                "output truncated to the first lines. Use start_line/end_line to read elsewhere."
            )

        logger.info(
            "tool read_file done requirement_id=%s commit=%s path=%r bytes=%s "
            "full_file elapsed_s=%.2f",
            _req_label(deps),
            deps.commit_sha[:7],
            path,
            size,
            time.monotonic() - started,
        )
        return content

    return _run_cached_tool(
        deps,
        "read_file",
        ("read_file", path, start_line, end_line),
        detail,
        _run,
    )


def _search_candidates(
    deps: CommitToolDeps,
    *,
    prefix: str,
    file_glob: str | None,
) -> tuple[list[str], str | None]:
    """Resolve candidate paths; return ``(paths, error_message)``."""
    all_files = deps.git_adapter.list_files_at_commit(deps.commit_sha)
    at_repo_root = prefix == ""

    if at_repo_root and not file_glob:
        if deps.path_globs:
            seen: set[str] = set()
            candidates: list[str] = []
            for glob_pattern in deps.path_globs:
                for path in all_files:
                    if path in seen:
                        continue
                    if glob_match(glob_pattern, path):
                        seen.add(path)
                        candidates.append(path)
            candidates.sort()
            return candidates, None
        return (
            [],
            "search_text at repository root requires file_glob (e.g. src/**/*.py) or use "
            "find_files / list_directory with a subdirectory path first.",
        )

    candidates = files_under_prefix(all_files, prefix)
    if file_glob:
        candidates = [candidate for candidate in candidates if glob_match(file_glob, candidate)]
    return candidates, None


def search_text(
    deps: CommitToolDeps,
    pattern: str,
    path: str = ".",
    file_glob: str | None = None,
) -> list[str]:
    """Search tracked UTF-8 files for a regex pattern."""
    query = pattern.strip()
    if not query:
        return []

    try:
        regex = re.compile(query)
    except re.error as exc:
        return [f"error: invalid regex: {exc}"]

    try:
        normalized = path.replace("\\", "/").strip()
        prefix = "" if normalized in {"", "."} else normalize_relpath(normalized)
    except ValueError as exc:
        return [f"error: {exc}"]

    detail = f"pattern={query!r} path={path!r} file_glob={file_glob!r}"

    def _run() -> list[str]:
        started = time.monotonic()
        candidates, error = _search_candidates(deps, prefix=prefix, file_glob=file_glob)
        if error is not None:
            logger.info(
                "tool search_text done requirement_id=%s commit=%s rejected %s",
                _req_label(deps),
                deps.commit_sha[:7],
                error,
            )
            return [f"error: {error}"]

        max_files = search_text_max_files()
        max_matches = search_text_max_matches()
        max_bytes = read_file_max_bytes()
        total_candidates = len(candidates)
        truncated_files = total_candidates > max_files
        if truncated_files:
            candidates = candidates[:max_files]

        matches: list[str] = []
        hit_match_cap = False
        skipped_blocked = 0
        skipped_large = 0
        for relpath in candidates:
            if _is_blocked_path(relpath):
                skipped_blocked += 1
                continue
            try:
                if deps.git_adapter.blob_size_at_commit(deps.commit_sha, relpath) > max_bytes:
                    skipped_large += 1
                    continue
            except Exception:
                continue

            try:
                content = deps.git_adapter.file_at_commit(deps.commit_sha, relpath)
            except Exception:
                continue

            for line_number, line in enumerate(content.splitlines(), start=1):
                if regex.search(line):
                    matches.append(f"{relpath}:{line_number}:{line}")
                    if len(matches) >= max_matches:
                        hit_match_cap = True
                        break
            if hit_match_cap:
                break

        elapsed_s = time.monotonic() - started
        logger.info(
            "tool search_text done requirement_id=%s commit=%s pattern=%r path=%r file_glob=%r "
            "candidates=%s scanned=%s matches=%s skipped_blocked=%s skipped_large=%s "
            "truncated_files=%s truncated_matches=%s elapsed_s=%.2f",
            _req_label(deps),
            deps.commit_sha[:7],
            query,
            path,
            file_glob,
            total_candidates,
            len(candidates),
            len(matches),
            skipped_blocked,
            skipped_large,
            truncated_files,
            hit_match_cap,
            elapsed_s,
        )
        if elapsed_s > 5.0:
            logger.warning(
                "tool search_text slow requirement_id=%s commit=%s elapsed_s=%.2f",
                _req_label(deps),
                deps.commit_sha[:7],
                elapsed_s,
            )

        if truncated_files:
            matches.append(
                f"warning: scanned {len(candidates)} of {total_candidates} files "
                f"(cap {max_files}); narrow path or file_glob.",
            )
        if hit_match_cap:
            matches.append(f"warning: truncated to {max_matches} matches; narrow your search.")
        if skipped_large:
            matches.append(
                f"warning: skipped {skipped_large} files over {max_bytes} bytes.",
            )
        return matches

    return _run_cached_tool(
        deps,
        "search_text",
        ("search_text", query, path, file_glob),
        detail,
        _run,
    )
