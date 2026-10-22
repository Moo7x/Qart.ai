"""Companion and case routes (src/api_companion.py), mounted by src/main.py.

Cases are served without `ground_truth` (only the grader reads it). After grading, the decision
route records the event in the engine in-process (`record_event`), so evidence, next case and path
update immediately; a recording error is returned to the client instead of being swallowed.
"""

import json
import logging
from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.api_engine import FlagRequest as EngineFlagRequest
from src.api_engine import FlagResponse, StoreDep, flag_event, record_event
from src.companion.agent import process_decision, process_message
from src.contract import Event, FlagName
from src.store import Store

router = APIRouter(tags=["companion"])
_log = logging.getLogger(__name__)

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"
INDEX_FILE = "index.json"
DEFAULT_USER = "u_aina"  # synthetic demo persona
DEFAULT_SCENARIO = "assistive"


def _load_case(case_id: str) -> dict[str, Any]:
    path = CASES_DIR / f"{case_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")
    case: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return case


def _public_case(case: dict[str, Any]) -> dict[str, Any]:
    """Strip ground_truth before returning to the client."""
    return {k: v for k, v in case.items() if k != "ground_truth"}


def _record(event: dict[str, Any], store: Store) -> list[dict[str, Any]]:
    """Validate the graded event against the contract and store it in the engine."""
    try:
        states = record_event(Event.model_validate(event), store)
    except HTTPException as error:
        _log.error("event %s rejected by the engine: %s", event.get("id"), error.detail)
        raise
    return [s.model_dump() for s in states]


# ── Cases ─────────────────────────────────────────────────────────────────────


@router.get("/api/cases")
def list_cases(user_id: str | None = None) -> list[dict[str, Any]]:
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        if path.name == INDEX_FILE:
            continue
        try:
            cases.append(_public_case(json.loads(path.read_text(encoding="utf-8"))))
        except (json.JSONDecodeError, OSError) as error:
            _log.warning("skipping unreadable case file %s: %s", path.name, error)
    return cases


@router.get("/api/cases/{case_id}")
def get_case(case_id: str) -> dict[str, Any]:
    return _public_case(_load_case(case_id))


# ── Companion ─────────────────────────────────────────────────────────────────


class MessageRequest(BaseModel):
    user_message: str
    case_id: str
    user_id: str = DEFAULT_USER
    scenario: str = DEFAULT_SCENARIO


class DecisionRequest(BaseModel):
    decision: str
    case_id: str
    flagged_rows: list[str] = []
    user_id: str = DEFAULT_USER
    scenario: str = DEFAULT_SCENARIO
    self_confidence_before: float | None = None


class SessionFlagRequest(BaseModel):
    flag: FlagName
    value: bool = True
    set_by: Literal["employee", "senior", "grader"] = "employee"
    user_id: str = DEFAULT_USER
    event_id: str | None = None  # default: the latest event recorded in this session


@router.post("/api/companion/{session_id}/message")
def companion_message(session_id: str, body: MessageRequest) -> dict[str, Any]:
    case = _load_case(body.case_id)
    return process_message(
        session_id=session_id,
        user_message=body.user_message,
        case=case,
        mode=case.get("mode", "practice"),
        user_id=body.user_id,
        scenario=body.scenario,
    )


@router.post("/api/companion/{session_id}/decision")
def companion_decision(session_id: str, body: DecisionRequest, store: StoreDep) -> dict[str, Any]:
    case = _load_case(body.case_id)
    result = process_decision(
        session_id=session_id,
        decision=body.decision,
        flagged_rows=body.flagged_rows,
        case=case,
        mode=case.get("mode", "practice"),
        user_id=body.user_id,
        scenario=body.scenario,
        self_confidence_before=body.self_confidence_before,
    )
    # event is None when a wrong practice decision is held back (missed_then_found flow).
    if result.get("event") is not None:
        result["skills"] = _record(result["event"], store)
    return result


@router.post("/api/companion/{session_id}/flag")
def flag_session(session_id: str, body: SessionFlagRequest, store: StoreDep) -> FlagResponse:
    """Flag an event (companion error / ambiguous case / data issue) so it stops counting."""
    event_id = body.event_id
    if event_id is None:
        in_session = [e for e in store.events_for(body.user_id) if e.session_id == session_id]
        if not in_session:
            raise HTTPException(status_code=404, detail=f"no event in session {session_id}")
        event_id = in_session[-1].id
    request = EngineFlagRequest(flag=body.flag, value=body.value, set_by=body.set_by)
    return flag_event(event_id, request, store)
