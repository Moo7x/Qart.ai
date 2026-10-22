"""Unit tests for src/companion/grader.py."""

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.companion.grader import grade

CASES_DIR = pathlib.Path(__file__).resolve().parent.parent / "cases"


@pytest.fixture
def case_003():
    return json.loads((CASES_DIR / "case_003.json").read_text())


@pytest.fixture
def case_001():
    return json.loads((CASES_DIR / "case_001.json").read_text())


@pytest.fixture
def case_006():
    return json.loads((CASES_DIR / "case_006.json").read_text())


# ── case_003 (correct_decision = "correct") ───────────────────────────────────


def test_correct_decision(case_003):
    result = grade(case_003, "correct", ["L4", "ADJ-7"])
    assert result["decision_correct"] is True
    assert all(se["outcome"] == "success" for se in result["skills_evidence"])
    assert result["issue_found_by"] == "user"


def test_wrong_decision_no_rows_flagged(case_003):
    result = grade(case_003, "sign_off", [])
    assert result["decision_correct"] is False
    assert all(se["outcome"] == "failure" for se in result["skills_evidence"])
    assert result["issue_found_by"] == "companion"


def test_wrong_decision_user_found_row(case_003):
    # Grader returns "failure" even when rows are flagged; agent.py upgrades to
    # "missed_then_found" once the user resubmits correctly.
    result = grade(case_003, "escalate", ["L4"])
    assert result["decision_correct"] is False
    assert all(se["outcome"] == "failure" for se in result["skills_evidence"])
    assert result["issue_found_by"] == "user"


def test_skills_evidence_skills(case_003):
    result = grade(case_003, "correct", [])
    skill_ids = {se["skill_id"] for se in result["skills_evidence"]}
    assert "transposition_check" in skill_ids
    assert "unsupported_adjustment" in skill_ids
    assert "ai_output_review" in skill_ids


# ── case_001 (clean case, correct_decision = "sign_off") ──────────────────────


def test_clean_case_correct(case_001):
    result = grade(case_001, "sign_off", [])
    assert result["decision_correct"] is True
    assert result["issue_found_by"] == "none"


def test_clean_case_wrong(case_001):
    result = grade(case_001, "correct", [])
    assert result["decision_correct"] is False


# ── case_006 (escalate) ────────────────────────────────────────────────────────


def test_escalate_correct(case_006):
    result = grade(case_006, "escalate", ["ADJ-1"])
    assert result["decision_correct"] is True
    assert result["issue_found_by"] == "user"


def test_escalate_wrong_sign_off(case_006):
    result = grade(case_006, "sign_off", [])
    assert result["decision_correct"] is False
    assert result["issue_found_by"] == "companion"


# ── grader never reads ground_truth implicitly ─────────────────────────────────


def test_grade_missing_ground_truth():
    """If ground_truth is missing, grade() returns failure gracefully."""
    case_no_gt = {"id": "x", "mode": "practice", "ledger": [], "bank": []}
    result = grade(case_no_gt, "sign_off", [])
    assert result["decision_correct"] is True  # default correct_decision is sign_off
    assert result["skills_evidence"] == []
