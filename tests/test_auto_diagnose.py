"""auto_diagnose output contract, validation and visible fallbacks (no network calls)."""

import json
from pathlib import Path
from typing import Any

import pytest

from src.companion import auto

CASE = Path(__file__).resolve().parent.parent / "cases" / "case_003.json"
PLAYBOOK = "src/companion/playbooks/playbook_v1.md"


def case() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(CASE.read_text(encoding="utf-8"))
    return data


def test_labels_are_error_types_only() -> None:
    labels = auto.issue_labels()
    assert "unsupported_adjustment" in labels and "transposition_check" in labels
    assert not set(labels) & auto.BEHAVIOUR_SKILLS


def test_clean_diagnosis_drops_unknown_labels_and_rows_and_keeps_consistency() -> None:
    raw = {
        "decision": "correct",
        "issue_types": ["unsupported_adjustment", "made_up"],
        "affected_rows": ["L4", "X99", {"row": "L5"}],
        "explanation": "x",
    }
    cleaned = auto.clean_diagnosis(raw, ["unsupported_adjustment"], ["L4", "ADJ-7"])
    assert cleaned["issue_types"] == ["unsupported_adjustment"]
    assert cleaned["affected_rows"] == ["L4"] and cleaned["has_issue"] is True
    signed = auto.clean_diagnosis(
        {**raw, "decision": "sign_off"}, ["unsupported_adjustment"], ["L4"]
    )
    assert signed == {
        "has_issue": False,
        "issue_types": [],
        "affected_rows": [],
        "decision": "sign_off",
        "explanation": "x",
    }
    assert auto.clean_diagnosis({"decision": "maybe"}, [], [])["decision"] == "escalate"


def test_schema_restricts_rows_to_the_case(monkeypatch: pytest.MonkeyPatch) -> None:
    schema = auto.diagnosis_schema(["a"], auto.row_ids(case()))
    rows = schema["json_schema"]["schema"]["properties"]["affected_rows"]["items"]["enum"]
    assert "L4" in rows and "ADJ-7" in rows and schema["json_schema"]["strict"] is True


def test_no_key_uses_rules_and_says_so(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    result = auto.auto_diagnose(case(), PLAYBOOK)
    assert result["source"] == "rule_based" and result["decision"] in auto.DECISIONS


def test_llm_failure_falls_back_visibly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_API_KEY", "test-key")

    def broken(*args: object, **kwargs: object) -> dict[str, Any]:
        raise RuntimeError("provider down")

    monkeypatch.setattr(auto, "_llm_diagnose", broken)
    result = auto.auto_diagnose(case(), PLAYBOOK)
    assert result["source"] == "rule_based_fallback"
    assert "provider down" in result["fallback_reason"]
