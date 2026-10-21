"""Person B: companion + cases API routes (src/api_companion.py).
Included automatically by src/main.py once this file exists.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.companion.agent import process_decision, process_message

router = APIRouter(tags=["companion"])
_log = logging.getLogger(__name__)


def _post_event_to_engine(event: dict) -> None:
    """Forward an event to Person A's engine.

    Tries direct import first (works after M1 merge); falls back to HTTP for
    standalone testing.  Logs errors clearly — never swallows them silently.
    """
    # Direct call — preferred; avoids HTTP round-trip after M1 merge.
    try:
        from src.store import get_store  # type: ignore[import-not-found]

        get_store().add_event(event)
        return
    except ImportError:
        pass  # engine not merged yet — fall through to HTTP
    except Exception as exc:
        _log.error("store.add_event failed for event %s: %s", event.get("id"), exc)
        raise

    # HTTP fallback — works when engine runs in the same uvicorn process.
    # Log failures but do NOT raise: grading succeeded; persistence is best-effort pre-M1.
    try:
        import httpx  # type: ignore[import-not-found]

        r = httpx.post("http://localhost:8000/api/events", json=event, timeout=2.0)
        r.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        _log.error("event %s not posted to engine: %s", event.get("id"), exc)

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"


def _load_case(case_id: str) -> dict:
    path = CASES_DIR / f"{case_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Case {case_id!r} not found")
    return json.loads(path.read_text())


def _public_case(case: dict) -> dict:
    """Strip ground_truth before returning to the client."""
    return {k: v for k, v in case.items() if k != "ground_truth"}


# ── Cases ─────────────────────────────────────────────────────────────────────

@router.get("/api/cases")
def list_cases(user_id: str | None = None):
    cases = []
    for path in sorted(CASES_DIR.glob("*.json")):
        if path.name == "index.json":
            continue
        try:
            cases.append(_public_case(json.loads(path.read_text())))
        except (json.JSONDecodeError, OSError):
            pass
    return cases


@router.get("/api/cases/{case_id}")
def get_case(case_id: str):
    return _public_case(_load_case(case_id))


# ── Companion ─────────────────────────────────────────────────────────────────

class MessageRequest(BaseModel):
    user_message: str
    case_id: str
    user_id: str = "u_aina"
    scenario: str = "assistive"


class DecisionRequest(BaseModel):
    decision: str
    case_id: str
    flagged_rows: list[str] = []
    user_id: str = "u_aina"
    scenario: str = "assistive"
    self_confidence_before: float | None = None


class FlagRequest(BaseModel):
    flag: str
    value: bool = True
    set_by: str = "employee"


@router.post("/api/companion/{session_id}/message")
def companion_message(session_id: str, body: MessageRequest):
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
def companion_decision(session_id: str, body: DecisionRequest):
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
        _post_event_to_engine(result["event"])
    return result


@router.post("/api/companion/{session_id}/flag")
def flag_session(session_id: str, body: FlagRequest):
    return {"ok": True, "session_id": session_id, "flag": body.flag, "value": body.value}
