"""Glob and path matching helpers for repository tools."""

from __future__ import annotations

import re
from pathlib import PurePosixPath


def normalize_relpath(path: str) -> str:
    posix = path.replace("\\", "/").strip("/")
    if posix and ".." in PurePosixPath(posix).parts:
        raise ValueError(f"Invalid path: {path!r}")
    return posix


def files_under_prefix(all_files: list[str], prefix: str) -> list[str]:
    if not prefix:
        return all_files
    root = f"{prefix}/"
    return [path for path in all_files if path == prefix or path.startswith(root)]


def _glob_segment(segment: str) -> str:
    return "/".join(
        re.escape(part).replace(r"\*", "[^/]*").replace(r"\?", "[^/]")
        for part in segment.split("/")
        if part
    )


def glob_match(pattern: str, file_path: str) -> bool:
    normalized_pattern = pattern.replace("\\", "/")
    normalized_path = file_path.replace("\\", "/")
    if "**" not in normalized_pattern:
        return PurePosixPath(normalized_path).match(normalized_pattern) or normalized_path == normalized_pattern

    if normalized_pattern == "**":
        return True

    if "/**/" in normalized_pattern:
        prefix, suffix = normalized_pattern.split("/**/", 1)
        regex = rf"^{_glob_segment(prefix)}/(?:.*/)?{_glob_segment(suffix)}$"
        return re.match(regex, normalized_path) is not None

    if normalized_pattern.endswith("/**"):
        prefix = normalized_pattern[:-3]
        return normalized_path == prefix or normalized_path.startswith(f"{prefix}/")

    if normalized_pattern.startswith("**/"):
        suffix = normalized_pattern[3:]
        regex = rf"^(?:.*/)?{_glob_segment(suffix)}$"
        return re.match(regex, normalized_path) is not None

    return PurePosixPath(normalized_path).match(normalized_pattern)
