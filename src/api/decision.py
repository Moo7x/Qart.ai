"""Decision-support routes: questions, sensitivity, what-if and plan comparison for one profile."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import _destination_or_query, require_profile
from src.changes.store import accepted_rows
from src.journey.store import (
    MAX_LEVEL,
    MAX_WEEKLY_HOURS,
    MIN_WEEKLY_HOURS,
    SkillClaim,
    update_profile,
)
from src.match.decision import best_questions, sensitivity, what_if
from src.match.engine import Scenario, score_role
from src.match.evidence import automation_evidence
from src.pack import load_pack
from src.pathway.optimise import compare_plans
from src.pathway.planner import plan_pathway

router = APIRouter(prefix="/api/profiles/{profile_id}")


class Answer(BaseModel):
    skill: str = Field(max_length=64)
    level: int = Field(ge=0, le=MAX_LEVEL)


class WhatIf(BaseModel):
    changes: dict[str, int | None] = {}
    weekly_hours: float | None = Field(default=None, ge=MIN_WEEKLY_HOURS, le=MAX_WEEKLY_HOURS)
    scenario: Scenario = "moderate"


@router.get("/questions")
def questions(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> list[dict[str, Any]]:
    data, destination = require_profile(engine, profile_id)
    evidence = automation_evidence(accepted_rows(engine, profile_id))
    found = best_questions(
        load_pack(), data.levels(), scenario, evidence, set(data.interests) or None, destination
    )
    return [q.__dict__ for q in found]


@router.post("/answer")
def answer(profile_id: str, body: Answer, engine: Engine = Depends(get_engine)) -> dict[str, str]:
    """The person's own answer to a question: a self-rated claim, never a verified level."""
    data, _ = require_profile(engine, profile_id)
    if body.skill not in load_pack().skills:
        raise HTTPException(status_code=422, detail="unknown skill")
    data.skills[body.skill] = SkillClaim(level=body.level, source="self")
    update_profile(engine, profile_id, data)
    return {"skill": body.skill, "level": str(body.level)}


@router.get("/sensitivity")
def rank_sensitivity(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    data, _ = require_profile(engine, profile_id)
    evidence = automation_evidence(accepted_rows(engine, profile_id))
    return sensitivity(load_pack(), data.levels(), scenario, evidence, set(data.interests) or None)


@router.post("/whatif")
def hypothetical(
    profile_id: str, body: WhatIf, engine: Engine = Depends(get_engine)
) -> dict[str, Any]:
    """Recompute with hypothetical changes; nothing is saved."""
    data, destination = require_profile(engine, profile_id)
    pack = load_pack()
    unknown = [s for s in body.changes if s not in pack.skills]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown skills: {', '.join(unknown)}")
    evidence = automation_evidence(accepted_rows(engine, profile_id))
    levels = data.levels()
    interests: set[str] | None = set(data.interests) or None
    out: dict[str, Any] = {
        "roles": what_if(pack, levels, body.changes, body.scenario, evidence, interests),
        "pathway": None,
    }
    if destination:
        role = pack.destination_roles[destination]
        hours = body.weekly_hours or data.weekly_hours
        then = {**levels, **body.changes}
        now_path = plan_pathway(
            pack,
            score_role(pack, role, levels, body.scenario, evidence),
            levels,
            data.weekly_hours,
            body.scenario,
            evidence,
        )
        then_path = plan_pathway(
            pack,
            score_role(pack, role, then, body.scenario, evidence),
            then,
            hours,
            body.scenario,
            evidence,
        )
        out["pathway"] = {
            "role_id": destination,
            "now": {"hours": now_path.total_hours, "weeks": now_path.weeks},
            "then": {"hours": then_path.total_hours, "weeks": then_path.weeks},
        }
    return out


@router.get("/plans")
def plans(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    role_id: str | None = Query(default=None, max_length=64),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    data, destination = require_profile(engine, profile_id)
    chosen = _destination_or_query(destination, role_id)
    pack = load_pack()
    evidence = automation_evidence(accepted_rows(engine, profile_id))
    levels = data.levels()
    match = score_role(pack, pack.destination_roles[chosen], levels, scenario, evidence)
    return compare_plans(pack, match, levels, data.weekly_hours, scenario, evidence)
