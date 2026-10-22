"""Integration tests for src/companion/agent.py — session-level behaviour."""

import json
import pathlib
import sys
import uuid

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from src.companion.agent import _sessions, get_or_create_session, process_decision

CASES_DIR = pathlib.Path(__file__).resolve().parent.parent / "cases"


@pytest.fixture
def case_003():
    return json.loads((CASES_DIR / "case_003.json").read_text())


@pytest.fixture
def case_001():
    return json.loads((CASES_DIR / "case_001.json").read_text())


def _sid() -> str:
    return f"test_{uuid.uuid4().hex[:8]}"


# ── missed_then_found two-step flow ───────────────────────────────────────────


def test_wrong_decision_holds_event(case_003):
    sid = _sid()
    result = process_decision(sid, "sign_off", [], case_003, "practice")
    assert result["event"] is None, "wrong practice decision must not emit an event"
    assert result["missed_and_walking_back"] is True
    assert result["decision_correct"] is False
    # The answer stays hidden while the user works through the help ladder.
    truth = case_003["ground_truth"]
    assert result["affected_rows"] == [] and result["correct_decision"] is None
    assert truth["explanation"] not in result["explanation"]
    assert not any(row in result["explanation"] for row in truth["affected_rows"])


def test_correct_after_miss_emits_missed_then_found(case_003):
    sid = _sid()
    # First: wrong decision — hold event
    r1 = process_decision(sid, "sign_off", [], case_003, "practice")
    assert r1["event"] is None

    # Second: correct decision — emit ONE event with missed_then_found
    r2 = process_decision(sid, "correct", ["L4", "ADJ-7"], case_003, "practice")
    assert r2["event"] is not None, "correct decision after a miss must emit an event"
    assert r2["decision_correct"] is True
    assert r2["missed_and_walking_back"] is False
    outcomes = {se["outcome"] for se in r2["event"]["skills_evidence"]}
    assert outcomes == {"missed_then_found"}, f"expected missed_then_found, got {outcomes}"


def test_second_wrong_still_holds_event(case_003):
    """Two consecutive wrong answers in practice mode: no event yet."""
    sid = _sid()
    r1 = process_decision(sid, "sign_off", [], case_003, "practice")
    assert r1["event"] is None
    r2 = process_decision(sid, "escalate", [], case_003, "practice")
    assert r2["event"] is None
    assert r2["missed_and_walking_back"] is True


def test_correct_first_attempt_emits_success(case_003):
    sid = _sid()
    result = process_decision(sid, "correct", ["L4"], case_003, "practice")
    assert result["event"] is not None
    assert result["decision_correct"] is True
    outcomes = {se["outcome"] for se in result["event"]["skills_evidence"]}
    assert outcomes == {"success"}


# ── checkin mode: wrong decision emits event immediately ──────────────────────


def test_checkin_wrong_emits_event_immediately(case_003):
    sid = _sid()
    # Override mode to checkin
    case = dict(case_003, mode="checkin")
    result = process_decision(sid, "sign_off", [], case, "checkin")
    assert result["event"] is not None, "checkin wrong decision must emit event immediately"
    assert result["decision_correct"] is False
    assert result["missed_and_walking_back"] is False


def test_checkin_help_level_always_zero(case_003):
    sid = _sid()
    case = dict(case_003, mode="checkin")
    session = get_or_create_session(sid, case, "checkin")
    # Force help_level up (should not happen in practice, but test the guard)
    session["help_level"] = 3
    session = get_or_create_session(sid, case, "checkin")
    assert session["help_level"] == 0


# ── per-case help state reset ─────────────────────────────────────────────────


def test_help_level_resets_on_new_case(case_003, case_001):
    sid = _sid()
    # Open case_003, advance help level
    session = get_or_create_session(sid, case_003, "practice")
    session["help_level"] = 3
    assert _sessions[sid]["help_level"] == 3

    # Open case_001 in the same session
    session2 = get_or_create_session(sid, case_001, "practice")
    assert session2["help_level"] == 0, "help_level must reset when opening a new case"


def test_messages_cleared_on_new_case(case_003, case_001):
    sid = _sid()
    session = get_or_create_session(sid, case_003, "practice")
    session["messages"] = [{"role": "user", "content": "hint?"}]

    get_or_create_session(sid, case_001, "practice")
    assert _sessions[sid]["messages"] == [], "messages must clear when switching cases"


# ── offline (no LLM key) replies ──────────────────────────────────────────────


def test_offline_answer_uses_only_this_case(case_001, monkeypatch):
    """The no-key reply at full help must come from this case's rows, not another case."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    from src.companion.agent import process_message

    sid = _sid()
    result = {}
    for _ in range(4):
        result = process_message(sid, "I'm stuck", case_001, "practice")
    assert result["help_level"] == 4
    assert "INV-1043" not in result["reply"]
    assert all(
        a.get("doc_ref") in {d["doc_ref"] for d in case_001["documents"]}
        for a in result["ui_actions"]
        if a["type"] == "open_document"
    )


def test_new_attempt_after_decision_starts_without_help(case_001, monkeypatch):
    """Reopening a decided case in the same session must not carry the old help level."""
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    from src.companion.agent import process_message

    sid = _sid()
    process_message(sid, "I'm stuck", case_001, "practice")
    process_decision(sid, "sign_off", [], case_001, "practice")
    assert process_message(sid, "hello", case_001, "practice")["help_level"] == 0
