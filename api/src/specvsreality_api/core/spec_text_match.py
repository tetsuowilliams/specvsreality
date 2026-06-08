"""Fuzzy matching of spec item text against spec markdown."""

from __future__ import annotations

from rapidfuzz import fuzz


def _exact_span(haystack: str, needle: str) -> tuple[int, int] | None:
    normalized_needle = needle.strip()
    if not normalized_needle:
        return None
    lower_haystack = haystack.lower()
    lower_needle = normalized_needle.lower()
    start = lower_haystack.find(lower_needle)
    if start < 0:
        return None
    return start, start + len(normalized_needle)


def find_item_span(
    spec_md: str,
    *,
    source_quote: str,
    text: str,
    min_score: float = 65.0,
) -> tuple[int, int] | None:
    """Locate the best matching character span for a spec item inside ``spec_md``."""
    best_span: tuple[int, int] | None = None
    best_score = min_score

    for candidate in (source_quote, text):
        normalized = candidate.strip()
        if not normalized:
            continue

        exact = _exact_span(spec_md, normalized)
        if exact is not None:
            return exact

        alignment = fuzz.partial_ratio_alignment(normalized, spec_md)
        if alignment.score > best_score:
            best_score = alignment.score
            best_span = (alignment.dest_start, alignment.dest_end)

    return best_span
