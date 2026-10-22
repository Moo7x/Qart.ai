"""Companion routes recorded in-process in the engine (integration of both parts)."""

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

CASES = Path(__file__).resolve().parent.parent / "cases"


def truth(case_id: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads((CASES / f"{case_id}.json").read_text(encoding="utf-8"))
    return data["ground_truth"]


def test_cases_never_expose_ground_truth(client: TestClient) -> None:
    cases = client.get("/api/cases").json()
    assert cases and all("ground_truth" not in c for c in cases)
    assert "ground_truth" not in client.get("/api/cases/case_003").json()


def test_decision_is_recorded_in_the_engine_and_returns_skills(client: TestClient) -> None:
    g = truth("checkin_001")
    body = {
        "decision": g["correct_decision"],
        "case_id": "checkin_001",
        "flagged_rows": g["affected_rows"],
    }
    result = client.post("/api/companion/s_test/decision", json=body).json()
    assert result["event"]["help_level_max"] == 0
    states = {s["skill_id"]: s for s in result["skills"]}
    assert states["unsupported_adjustment"]["counted_events"] == 1
    skills = client.get("/api/skills/u_aina").json()
    assert (
        next(s for s in skills if s["skill_id"] == "unsupported_adjustment")["counted_events"] == 1
    )


def test_wrong_practice_decision_is_held_back_until_found(client: TestClient) -> None:
    first = client.post(
        "/api/companion/s_hold/decision", json={"decision": "sign_off", "case_id": "case_003"}
    ).json()
    assert first["event"] is None and "skills" not in first


def test_flag_marks_the_latest_session_event_so_it_stops_counting(client: TestClient) -> None:
    g = truth("checkin_001")
    client.post(
        "/api/companion/s_flag/decision",
        json={
            "decision": g["correct_decision"],
            "case_id": "checkin_001",
            "flagged_rows": g["affected_rows"],
        },
    )
    flagged = client.post(
        "/api/companion/s_flag/flag", json={"flag": "companion_error", "set_by": "employee"}
    )
    assert flagged.status_code == 200
    assert flagged.json()["event"]["flags"]["companion_error"] is True
    state = next(s for s in flagged.json()["skills"] if s["skill_id"] == "unsupported_adjustment")
    assert state["counted_events"] == 0
    missing = client.post("/api/companion/s_none/flag", json={"flag": "ambiguous_case"})
    assert missing.status_code == 404


def test_demo_reset_clears_companion_sessions(client: TestClient) -> None:
    msg = {"user_message": "I'm stuck", "case_id": "case_003"}
    assert client.post("/api/companion/s_reset/message", json=msg).json()["help_level"] == 1
    client.post("/api/demo/reset").raise_for_status()
    assert client.post("/api/companion/s_reset/message", json=msg).json()["help_level"] == 1
