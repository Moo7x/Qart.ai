"""CV routes: the current draft with its diff, accepted versions, and accepting a draft."""

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import require_profile
from src.cv.draft import accept, build_draft, diff, select_changes, versions
from src.goal.store import get_goal
from src.journey.progress import get_progress
from src.pack import load_pack

router = APIRouter(prefix="/api/profiles/{profile_id}/cv")


def _draft(engine: Engine, profile_id: str) -> dict[str, list[str]]:
    data, destination = require_profile(engine, profile_id)
    goal = get_goal(engine, profile_id)
    done = get_progress(engine, profile_id)["done"]
    return build_draft(load_pack(), data, destination, goal["role_title"] if goal else None, done)


@router.get("")
def cv(profile_id: str, engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    draft = _draft(engine, profile_id)
    saved = versions(engine, profile_id)
    last = saved[-1]["sections"] if saved else None
    return {
        "draft": draft,
        "diff": diff(last, draft),
        "unchanged": last == draft,
        "current": last,  # the last accepted version: what the PDF prints
        "versions": [{"version": v["version"], "accepted_at": v["accepted_at"]} for v in saved],
    }


class AcceptIn(BaseModel):
    """Which suggested changes the person leaves out; by default every change is accepted."""

    skip_added: list[str] = Field(default_factory=list, max_length=200)
    keep_removed: list[str] = Field(default_factory=list, max_length=200)


@router.post("/accept")
def accept_draft(
    profile_id: str, body: AcceptIn | None = None, engine: Engine = Depends(get_engine)
) -> dict[str, int]:
    draft = _draft(engine, profile_id)
    saved = versions(engine, profile_id)
    choice = body or AcceptIn()
    sections = select_changes(
        saved[-1]["sections"] if saved else None, draft, choice.skip_added, choice.keep_removed
    )
    return {"version": accept(engine, profile_id, sections)}
