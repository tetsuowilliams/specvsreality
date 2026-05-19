"""Cheap pre-filter: is this blob worth an LLM call for this requirement?"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pathspec import PathSpec

from specvsreality_repositories.models.requirement_version import RequirementVersion


class CandidateFilter:
    """Decide whether a blob is plausibly relevant to a requirement.

    Filtering happens in three layers, cheapest first:

    1. Reject blobs above a size cap (default 200 KiB) -- almost always
       generated artifacts for which the LLM call is wasteful.
    2. Reject blobs whose path extension is on the binary deny-list.
    3. If the requirement has ``path_globs`` set, require the blob path to
       match at least one of them under gitignore semantics. An empty / missing
       glob list disables this check (treated as "no hint").

    Layers (1) and (2) work even when the path is unknown; layer (3) requires
    a path. Globs are loose discovery hints from an LLM, not authoritative
    routing rules, so we use ``pathspec``'s gitignore matcher (``src/**/*.py``
    matches both ``src/foo.py`` and ``src/a/b/c.py``).
    """

    DEFAULT_MAX_BYTES = 200 * 1024
    _BINARY_EXTENSIONS: frozenset[str] = frozenset(
        {
            "png", "jpg", "jpeg", "gif", "webp", "ico", "svg",
            "pdf", "zip", "gz", "tar", "tgz", "wasm",
            "ttf", "otf", "woff", "woff2",
            "mp3", "mp4", "mov", "avi",
        }
    )

    def __init__(
        self,
        *,
        max_bytes: int = DEFAULT_MAX_BYTES,
        binary_extensions: Iterable[str] | None = None,
    ) -> None:
        self._max_bytes = max_bytes
        self._binary_extensions: frozenset[str] = (
            frozenset(ext.lower() for ext in binary_extensions)
            if binary_extensions is not None
            else self._BINARY_EXTENSIONS
        )

    def is_candidate(
        self,
        *,
        blob_size_bytes: int | None,
        path_hint: str | None,
        requirement_version: RequirementVersion,
    ) -> bool:
        if blob_size_bytes is not None and blob_size_bytes > self._max_bytes:
            return False

        globs = self._globs_for(requirement_version)

        if path_hint is None:
            return not globs

        if self._is_binary_path(path_hint):
            return False

        if not globs:
            return True

        normalized = path_hint.replace("\\", "/").lstrip("/")
        spec = PathSpec.from_lines("gitignore", globs)
        return spec.match_file(normalized)

    def _is_binary_path(self, path: str) -> bool:
        ext = path.rsplit(".", 1)[-1].lower() if "." in path else ""
        return ext in self._binary_extensions

    @staticmethod
    def _globs_for(requirement_version: RequirementVersion) -> Sequence[str]:
        raw = requirement_version.path_globs or ()
        return [g for g in raw if isinstance(g, str) and g.strip()]
