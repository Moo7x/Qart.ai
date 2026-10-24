"""Goal routes: save a target role, optionally with a pasted public posting, and check it."""

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from src.api.evidence import get_engine, get_settings
from src.api.journey import require_profile
from src.changes.store import accepted_rows
from src.config import Settings
from src.goal.posting import (
    MAX_POSTING_CHARS,
    PostingCheck,
    PostingRequirement,
    coverage,
    read_requirements,
    stepping_stones,
)
from src.goal.store import get_goal, save_goal
from src.match.engine import Scenario
from src.match.evidence import automation_evidence
from src.pack import load_pack

router = APIRouter(prefix="/api/profiles/{profile_id}/goal")


class GoalIn(BaseModel):
    role_title: str = Field(min_length=2, max_length=120)
    company: str = Field(default="", max_length=120)
    location: str = Field(default="", max_length=120)
    why: str = Field(default="", max_length=500)
    posting_text: str = Field(default="", max_length=MAX_POSTING_CHARS)
    posting_url: str = Field(default="", max_length=500)
    posting_date: str = Field(default="", max_length=20)  # as stated on the posting


def _view(engine: Engine, profile_id: str, scenario: Scenario) -> dict[str, Any]:
    data, _ = require_profile(engine, profile_id)
    goal = get_goal(engine, profile_id)
    if goal is None:
        return {"goal": None}
    check = PostingCheck(
        goal["engine"],
        goal["note"],
        [
            PostingRequirement(
                **{k: r[k] for k in ("quote", "skill", "skill_name", "essential", "required_level")}
            )
            for r in goal["requirements"]
        ],
    )
    levels = data.levels()
    evidence = automation_evidence(accepted_rows(engine, profile_id))
    pack = load_pack()
    result = coverage(check, levels) if check.requirements else None
    return {
        "goal": {k: goal[k] for k in GoalIn.model_fields},
        "coverage": result,
        "stages": goal.get("stages", []),
        "stepping_stones": stepping_stones(pack, check, levels, scenario, evidence)
        if result
        else [],
    }


@router.put("")
def set_goal(
    profile_id: str,
    body: GoalIn,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    require_profile(engine, profile_id)
    found = (
        read_requirements(load_pack(), body.posting_text, settings)
        if body.posting_text.strip()
        else PostingCheck("none", "no posting pasted")
    )
    save_goal(
        engine,
        profile_id,
        {
            **body.model_dump(),
            "engine": found.engine,
            "note": found.note,
            "requirements": [asdict(r) for r in found.requirements],
            "stages": found.stages,
        },
    )
    return _view(engine, profile_id, scenario)


@router.get("")
def goal(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    return _view(engine, profile_id, scenario)
