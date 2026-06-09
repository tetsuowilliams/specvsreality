"""Fuzzy matching of spec item text against spec markdown."""

from __future__ import annotations

from typing import TypedDict

from rapidfuzz import fuzz


class TextSpan(TypedDict):
    start: int
    end: int


class HighlightSpans(TypedDict):
    spec: TextSpan | None
    tasks: TextSpan | None
    plan: TextSpan | None


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


def _fuzzy_span(
    haystack: str,
    needle: str,
    *,
    min_score: float,
) -> tuple[int, int] | None:
    """Find the best matching window for ``needle`` inside ``haystack``."""
    normalized_needle = needle.strip()
    if not normalized_needle:
        return None

    alignment = fuzz.partial_ratio_alignment(normalized_needle, haystack)
    if alignment is None or alignment.score < min_score:
        return None

    needle_len = len(normalized_needle)
    lower_needle = normalized_needle.lower()
    best_score = min_score
    best_span: tuple[int, int] | None = None

    hint_start = alignment.dest_start
    hint_end = alignment.dest_end
    margin = needle_len
    search_start = max(0, hint_start - margin)
    search_end = min(len(haystack), hint_end + margin)
    local = haystack[search_start:search_end]
    local_len = len(local)

    min_window = max(1, int(needle_len * 0.7))
    max_window = min(local_len, int(needle_len * 1.4) + 1)
    for window_size in range(min_window, max_window + 1):
        for offset in range(local_len - window_size + 1):
            score = fuzz.ratio(lower_needle, local[offset : offset + window_size].lower())
            if score > best_score:
                best_score = score
                start = search_start + offset
                best_span = (start, start + window_size)

    return best_span


def _span_length(span: tuple[int, int]) -> int:
    return span[1] - span[0]


def find_item_span(
    spec_md: str,
    *,
    source_quote: str,
    text: str,
    min_score: float = 65.0,
) -> tuple[int, int] | None:
    """Locate the best matching character span for a spec item inside ``spec_md``."""
    exact_spans: list[tuple[int, int]] = []
    best_fuzzy_span: tuple[int, int] | None = None
    best_fuzzy_score = min_score

    for candidate in (text, source_quote):
        normalized = candidate.strip()
        if not normalized:
            continue

        exact = _exact_span(spec_md, normalized)
        if exact is not None:
            exact_spans.append(exact)
            continue

        fuzzy = _fuzzy_span(spec_md, normalized, min_score=min_score)
        if fuzzy is None:
            continue

        fuzzy_score = fuzz.ratio(normalized.lower(), spec_md[fuzzy[0] : fuzzy[1]].lower())
        if fuzzy_score > best_fuzzy_score or (
            fuzzy_score == best_fuzzy_score
            and best_fuzzy_span is not None
            and _span_length(fuzzy) > _span_length(best_fuzzy_span)
        ):
            best_fuzzy_score = fuzzy_score
            best_fuzzy_span = fuzzy
        elif fuzzy_score == best_fuzzy_score and best_fuzzy_span is None:
            best_fuzzy_score = fuzzy_score
            best_fuzzy_span = fuzzy

    if exact_spans:
        return max(exact_spans, key=_span_length)

    return best_fuzzy_span


def _span_to_dict(span: tuple[int, int] | None) -> TextSpan | None:
    if span is None:
        return None
    return TextSpan(start=span[0], end=span[1])


def compute_highlight_spans(
    *,
    spec_md: str,
    tasks_md: str | None,
    plan_md: str | None,
    source_quote: str,
    text: str,
) -> HighlightSpans:
    """Compute UI highlight spans for a spec item across all bundle documents."""

    def _for_document(markdown: str | None) -> TextSpan | None:
        if not markdown:
            return None
        return _span_to_dict(
            find_item_span(markdown, source_quote=source_quote, text=text),
        )

    return HighlightSpans(
        spec=_for_document(spec_md),
        tasks=_for_document(tasks_md),
        plan=_for_document(plan_md),
    )
