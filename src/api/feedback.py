"""Feedback routes: anyone can report; the admin reviews, evaluates and releases corrections."""

import hmac
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from src.api.evidence import get_engine, get_settings
from src.changes.store import baseline_cutoff
from src.config import Settings
from src.feedback.service import (
    KINDS,
    decide,
    evaluate_course_removal,
    preferences,
    queue,
    record,
    releases,
)
from src.journey.store import get_profile

router = APIRouter(prefix="/api")


class Report(BaseModel):
    kind: Literal[
        "not_my_goal",
        "impractical_schedule",
        "course_unavailable",
        "wrong_skill_mapping",
        "unsupported_claim",
        "wrong_number",
    ]
    target_type: Literal[
        "role", "course", "skill", "evidence", "explanation", "requirement", "plan"
    ]
    target_id: str = Field(min_length=1, max_length=128)
    page: str = Field(min_length=1, max_length=32)
    message: str = Field(default="", max_length=1000)
    profile_id: str | None = Field(default=None, max_length=64)


class Decision(BaseModel):
    decision: Literal["accept", "reject"]
    note: str = Field(default="", max_length=1000)


def require_admin(
    settings: Settings = Depends(get_settings), x_admin_token: str | None = Header(default=None)
) -> None:
    if not settings.admin_token:
        raise HTTPException(
            status_code=503, detail="review is disabled: QART_ADMIN_TOKEN is not set"
        )
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=403, detail="admin token required")


@router.post("/feedback", status_code=201)
def report(body: Report, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    profile = body.profile_id if body.profile_id and get_profile(engine, body.profile_id) else None
    cutoff = baseline_cutoff(engine, profile) if profile else None
    out = record(
        engine,
        profile,
        body.kind,
        body.target_type,
        body.target_id,
        body.page,
        body.message,
        cutoff,
    )
    out["explanation"] = (
        "Saved as your preference: it changes what you see, not the data for anyone else."
        if KINDS[body.kind] == "preference"
        else "Sent for review. A correction is tested on fixed example profiles before release."
    )
    return out


@router.get("/profiles/{profile_id}/preferences")
def my_preferences(profile_id: str, engine: Engine = Depends(get_engine)) -> dict[str, list[str]]:
    return preferences(engine, profile_id)


@router.get("/feedback", dependencies=[Depends(require_admin)])
def review_queue(engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    return {"queue": queue(engine), "releases": releases(engine)}


@router.get("/feedback/{feedback_id}/evaluate", dependencies=[Depends(require_admin)])
def evaluate(feedback_id: int, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    item = next((q for q in queue(engine) if q["id"] == feedback_id), None)
    if item is None:
        raise HTTPException(status_code=404, detail="unknown feedback")
    if not item["proposal"]:
        return {
            "proposal": None,
            "evaluation": None,
            "note": "no automatic correction for this kind",
        }
    return {
        "proposal": item["proposal"],
        "evaluation": evaluate_course_removal(item["proposal"]["course_id"]),
    }


@router.post("/feedback/{feedback_id}/decide", dependencies=[Depends(require_admin)])
def decide_feedback(
    feedback_id: int, body: Decision, engine: Engine = Depends(get_engine)
) -> dict[str, Any]:
    try:
        return decide(engine, feedback_id, body.decision == "accept", body.note)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
