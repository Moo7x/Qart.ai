"""CV phrases outside our skill list are listed, never dropped silently, and never invented."""

import json
from pathlib import Path
from typing import Any

from src.config import Settings
from src.intake import extract as extract_mod
from src.pack import load_pack

NUR = (Path(__file__).parent.parent / "data" / "samples" / "nur.txt").read_text(encoding="utf-8")


def model(unmatched: list[str]) -> extract_mod.Complete:
    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        assert "unmatched" in schema["required"]
        return json.dumps(
            {
                "current_role": "other",
                "years_experience": 6,
                "skills": [],
                "interests": [],
                "unmatched": unmatched,
            }
        )

    return complete


def test_phrases_in_the_cv_are_listed_once(settings: Settings) -> None:
    answer = ["VLOOKUP", "vlookup", "customer communication"]
    result = extract_mod.extract(load_pack(), NUR, settings, model(answer))
    assert result.unmatched == ["VLOOKUP", "customer communication"]


def test_phrases_not_in_the_cv_or_too_long_are_dropped(settings: Settings) -> None:
    answer = ["Kubernetes", "SAP FI", "x", "VLOOK", "a" * 81]
    result = extract_mod.extract(load_pack(), NUR, settings, model(answer))
    assert result.unmatched == ["SAP FI"]  # "VLOOK" is only part of a word


def test_keyword_fallback_says_it_cannot_list_them(settings: Settings) -> None:
    result = extract_mod.extract(load_pack(), NUR, settings)
    assert result.unmatched == []
    assert extract_mod.KEYWORD_UNMATCHED_NOTE in result.note
