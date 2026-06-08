"""Unit tests for spec item span matching."""

from __future__ import annotations

from specvsreality_api.core.spec_text_match import find_item_span


def test_find_item_span_exact_source_quote() -> None:
    spec_md = "# Greeting\n\nThe system shall greet users on startup."
    span = find_item_span(
        spec_md,
        source_quote="greet users on startup",
        text="System greets users when starting",
    )
    assert span == (29, 51)


def test_find_item_span_fuzzy_when_text_differs() -> None:
    spec_md = "# Auth\n\nUsers must authenticate with a valid password before access."
    span = find_item_span(
        spec_md,
        source_quote="authenticate with password",
        text="Users must authenticate with a valid password before access",
    )
    assert span is not None
    start, end = span
    matched = spec_md[start:end].lower()
    assert "authenticate" in matched
    assert "password" in matched


def test_find_item_span_returns_none_for_empty_candidates() -> None:
    assert find_item_span("# Title", source_quote="", text="") is None
