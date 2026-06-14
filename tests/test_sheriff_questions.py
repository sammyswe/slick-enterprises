"""Tests for clarifying-question extraction."""

from gateway.sheriff_flow import (
    DEFAULT_CLARIFYING_QUESTIONS,
    extract_clarifying_questions,
    format_clarifying_reply,
)


def test_extract_numbered_questions():
    text = """
Sheriff S here — preamble we should skip.
---
**1. What are you selling?**
- bullet we ignore
**2. Who is the customer?**
Reply with answers later.
"""
    qs = extract_clarifying_questions(text)
    assert len(qs) == 2
    assert qs[0].startswith("1.")
    assert "selling" in qs[0]
    assert qs[1].startswith("2.")


def test_fallback_format_always_has_questions():
    reply = format_clarifying_reply([])
    for q in DEFAULT_CLARIFYING_QUESTIONS:
        assert q in reply
