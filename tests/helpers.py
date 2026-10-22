"""Shared test builders for synthetic events and the golden-journey fixture."""

import json
from pathlib import Path
from typing import Any

from src.contract import CaseMode, Event, Outcome

FIXTURES = Path(__file__).resolve().parent / "fixtures"


def golden_journey_raw() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (FIXTURES / "golden_journey_events.json").read_text(encoding="utf-8")
    )
    return data


def golden_journey_events(include_second_checkin: bool = False) -> list[Event]:
    raw = golden_journey_raw()
    events = [Event.model_validate(e) for e in raw["events"]]
    if include_second_checkin:
        events.append(Event.model_validate(raw["optional_second_checkin"]))
    return events


def make_event(
    number: int,
    *,
    skill_id: str = "unsupported_adjustment",
    outcome: Outcome = "success",
    help_level: int = 0,
    case_id: str | None = None,
    session_id: str = "s_1",
    mode: CaseMode = "practice",
    user_id: str = "u_test",
    companion_error: bool = False,
    ambiguous_case: bool = False,
    data_issue: bool = False,
) -> Event:
    """One synthetic single-skill event; `number` orders events in time (minutes)."""
    return Event.model_validate(
        {
            "id": f"ev_{number:04d}",
            "user_id": user_id,
            "case_id": case_id or f"case_{number:03d}",
            "mode": mode,
            "scenario": "assistive",
            "timestamp": f"2026-10-22T10:{number:02d}:00+08:00",
            "help_level_max": help_level,
            "user_decision": "correct",
            "decision_correct": outcome == "success",
            "skills_evidence": [
                {"skill_id": skill_id, "outcome": outcome, "help_level": help_level}
            ],
            "session_id": session_id,
            "flags": {
                "companion_error": companion_error,
                "ambiguous_case": ambiguous_case,
                "data_issue": data_issue,
            },
        }
    )
