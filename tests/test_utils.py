"""Tests for the template helpers in src/utils.py."""

from src.utils import format_greeting, summarize


def test_format_greeting() -> None:
    assert format_greeting("Demo") == "Welcome to Demo!"


def test_summarize() -> None:
    result = summarize([1, 2, 3])
    assert result["count"] == 3
    assert result["average"] == 2.0


def test_summarize_empty() -> None:
    assert summarize([])["count"] == 0
