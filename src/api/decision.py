"""Decision-support routes: questions, sensitivity, what-if and plan comparison for one profile."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import chosen_role, require_person, require_profile
from src.journey.events import record_event
from src.journey.progress import get_progress, save_progress
from src.journey.store import (
    MAX_LEVEL,
    MAX_WEEKLY_HOURS,
    MIN_WEEKLY_HOURS,
    SkillClaim,
    update_profile,
)
from src.match.decision import best_questions, sensitivity, what_if
from src.match.engine import Scenario
from src.pack import Pack, load_pack
from src.pathway.optimise import compare_plans

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
    p = require_person(engine, profile_id)
    found = best_questions(
        p.pack, p.levels(), scenario, p.evidence, set(p.data.interests) or None, p.destination
    )
    return [q.__dict__ for q in found]


@router.post("/answer")
def answer(profile_id: str, body: Answer, engine: Engine = Depends(get_engine)) -> dict[str, str]:
    """The person's own answer to a question: a self-rated claim, never a verified level."""
    data, _ = require_profile(engine, profile_id)
    if body.skill not in load_pack().skills:
        raise HTTPException(status_code=422, detail=f"unknown skill: {body.skill}")
    before = data.skills[body.skill].level if body.skill in data.skills else None
    data.skills[body.skill] = SkillClaim(level=body.level, source="self")
    update_profile(engine, profile_id, data)
    record_event(
        engine,
        profile_id,
        "level_changed",
        body.skill,
        before,
        {"level": body.level, "source": "self"},
    )
    return {"skill": body.skill, "level": str(body.level)}


@router.get("/sensitivity")
def rank_sensitivity(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    p = require_person(engine, profile_id)
    return sensitivity(p.pack, p.levels(), scenario, p.evidence, set(p.data.interests) or None)


@router.post("/whatif")
def hypothetical(
    profile_id: str, body: WhatIf, engine: Engine = Depends(get_engine)
) -> dict[str, Any]:
    """Recompute with hypothetical changes; nothing is saved."""
    person = require_person(engine, profile_id)
    pack, data, destination = person.pack, person.data, person.destination
    unknown = [s for s in body.changes if s not in pack.skills]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown skills: {', '.join(unknown)}")
    interests: set[str] | None = set(data.interests) or None
    out: dict[str, Any] = {
        "roles": what_if(
            pack, person.levels(), body.changes, body.scenario, person.evidence, interests
        ),
        "pathway": None,
    }
    if destination:
        # A what-if level is the person's own hypothesis: an unevidenced claim.
        then = person.with_claims(
            {k: SkillClaim(level=v, source="self") for k, v in body.changes.items()}
        )
        now_path = person.plan(person.score(destination, body.scenario), body.scenario)
        then_path = then.plan(
            then.score(destination, body.scenario),
            body.scenario,
            weekly_hours=body.weekly_hours or data.weekly_hours,
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
    person = require_person(engine, profile_id)
    data = person.data
    match = person.score(chosen_role(person, role_id), scenario)
    return compare_plans(
        person.pack,
        match,
        data.skills,
        data.weekly_hours,
        scenario,
        person.evidence,
        data.situation,
    )


class ProgressIn(BaseModel):
    done: list[str] = Field(default=[], max_length=200)
    paused: bool = False
    # Steps passed with "continue anyway" (C5). None keeps what is stored.
    skipped: list[str] | None = Field(default=None, max_length=200)


def _known_step(pack: Pack, step_id: str) -> bool:
    """A course id, or a practice step id for a pack skill and a practice level."""
    if step_id in pack.courses:
        return True
    kind, _, rest = step_id.partition(":")
    skill, _, level = rest.partition(":")
    return kind == "practice" and skill in pack.skills and level in ("3", "4")


def _progress_view(engine: Engine, profile_id: str, scenario: Scenario) -> dict[str, Any]:
    """Three separate measures: plan completion, requirement coverage, open questions."""
    person = require_person(engine, profile_id)
    data, destination = person.data, person.destination
    saved = get_progress(engine, profile_id)
    out: dict[str, Any] = {**saved, "plan": None}
    if not destination:
        return out
    match = person.score(destination, scenario)
    path = person.plan(match, scenario)
    steps = [(s.course.id, s.course.title, s.hours) for s in path.steps]
    done = [c for c, _, _ in steps if c in saved["done"]]
    left = [(c, t, h) for c, t, h in steps if c not in saved["done"]]
    week: list[dict[str, Any]] = []
    budget = data.weekly_hours
    for course_id, title, hours in left:  # this week's milestone: next steps within the hours
        if week and sum(w["hours"] for w in week) + hours > budget:
            break
        week.append({"id": course_id, "title": title, "hours": hours})
    out["plan"] = {
        "role_id": destination,
        "steps": len(steps),
        "steps_done": len(done),
        "hours": path.total_hours,
        "hours_done": round(sum(h for c, _, h in steps if c in done), 1),
        "coverage": match.fit,
        "open_questions": sum(r.claimed is None for r in match.requirements),
        "this_week": week,
        "weekly_hours": budget,
    }
    return out


@router.get("/progress")
def progress(
    profile_id: str,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    return _progress_view(engine, profile_id, scenario)


@router.put("/progress")
def set_progress(
    profile_id: str,
    body: ProgressIn,
    scenario: Scenario = Query(default="moderate"),
    engine: Engine = Depends(get_engine),
) -> dict[str, Any]:
    require_profile(engine, profile_id)
    pack = load_pack()
    skipped = None if body.skipped is None else [s for s in body.skipped if _known_step(pack, s)]
    done = [c for c in body.done if c in pack.courses]
    saved = get_progress(engine, profile_id)
    save_progress(engine, profile_id, done, body.paused, skipped)
    for course in sorted(set(done) - set(saved["done"])):
        record_event(engine, profile_id, "course_done", course)
    for course in sorted(set(saved["done"]) - set(done)):
        record_event(engine, profile_id, "course_undone", course)
    for step in sorted(set(skipped or []) - set(saved["skipped"])):
        record_event(engine, profile_id, "step_skipped", step)
    return _progress_view(engine, profile_id, scenario)
