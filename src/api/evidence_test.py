"""Change test: recompute roles, weights and pathway with test evidence values; nothing is saved.

docs/PHASE2_PLAN.md A3 and contract C7. Owner: A (p2-ai-experience). Registered in
src/app.py in Stage 0; routes are added here only.

A judge can ask "change the trend data now: what should change?". This route answers it with the
real engine: the stored evidence is copied, one or more observed AI-use shares are replaced by
test values, and the unchanged `rank_roles`, `score_role` and `plan_pathway` run on both. Stored
observations, the profile and the accepted journey are never touched.
"""

from dataclasses import replace
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import evidence_for, require_profile
from src.match.engine import Evidence, RoleMatch, Scenario, rank_roles
from src.pack import Pack, load_pack
from src.pathway.planner import plan_pathway

router = APIRouter(prefix="/api/profiles/{profile_id}")

TEST_LABEL = "Test value, not real data"
MAX_OVERRIDES = 10
WEIGHT_DECIMALS = 3


class Override(BaseModel):
    kind: Literal["occupation_share", "task_share"]
    key: str = Field(min_length=1, max_length=32)  # an O*NET-SOC code or an O*NET task id
    value: float = Field(ge=0, le=100)  # % of AI use that is automation-style


class EvidenceTestIn(BaseModel):
    scenario: Scenario = "moderate"
    overrides: list[Override] = Field(min_length=1, max_length=MAX_OVERRIDES)


class RoleRank(BaseModel):
    role_id: str
    title: str
    rank: int
    fit: float


class Ranking(BaseModel):
    roles: list[RoleRank]


class WeightChange(BaseModel):
    role_id: str
    skill: str
    skill_name: str
    before: float
    after: float


class PathwayChange(BaseModel):
    role_id: str
    title: str
    before: list[str]
    after: list[str]
    titles: dict[str, str]  # course id -> title, for every course in either plan
    fit_after_before: float
    fit_after_after: float


class EvidenceTestOut(BaseModel):
    label: str
    scenario: Scenario
    overrides: list[Override]
    previous: dict[str, float | None]  # the stored value each override replaced (None = missing)
    before: Ranking
    after: Ranking
    weights: list[WeightChange]
    pathway: PathwayChange | None


def _check_keys(pack: Pack, overrides: list[Override]) -> None:
    socs = {role.soc for role in pack.destination_roles.values()}
    tasks = pack.task_ids()
    unknown = [
        o.key
        for o in overrides
        if (o.kind == "occupation_share" and o.key not in socs)
        or (o.kind == "task_share" and o.key not in tasks)
    ]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown keys: {', '.join(unknown)}")


def apply_overrides(evidence: Evidence, overrides: list[Override]) -> Evidence:
    """A copy of the evidence with the test values in place; the original is not changed."""
    occupation = dict(evidence.automation_share)
    task = dict(evidence.task_automation)
    for o in overrides:
        (occupation if o.kind == "occupation_share" else task)[o.key] = o.value
    return replace(evidence, automation_share=occupation, task_automation=task)


def _ranking(matches: list[RoleMatch]) -> Ranking:
    return Ranking(
        roles=[
            RoleRank(role_id=m.role_id, title=m.title, rank=i, fit=m.fit)
            for i, m in enumerate(matches, 1)
        ]
    )


def _weights(before: list[RoleMatch], after: list[RoleMatch]) -> list[WeightChange]:
    then = {m.role_id: {r.skill: r.weight for r in m.requirements} for m in after}
    out = []
    for match in before:
        for req in match.requirements:
            new = then[match.role_id][req.skill]
            if round(new, WEIGHT_DECIMALS) != round(req.weight, WEIGHT_DECIMALS):
                out.append(
                    WeightChange(
                        role_id=match.role_id,
                        skill=req.skill,
                        skill_name=req.skill_name,
                        before=round(req.weight, WEIGHT_DECIMALS),
                        after=round(new, WEIGHT_DECIMALS),
                    )
                )
    return out


@router.post("/evidence-test")
def evidence_test(
    profile_id: str, body: EvidenceTestIn, engine: Engine = Depends(get_engine)
) -> EvidenceTestOut:
    """Before → after for the person's ranking, weights and plan under test evidence values."""
    data, destination = require_profile(engine, profile_id)
    pack = load_pack()
    _check_keys(pack, body.overrides)
    stored = evidence_for(engine, profile_id)
    tested = apply_overrides(stored, body.overrides)
    levels = data.levels()
    interests: set[str] | None = set(data.interests) or None
    before = rank_roles(pack, levels, body.scenario, stored, interests)
    after = rank_roles(pack, levels, body.scenario, tested, interests)
    focus = destination or before[0].role_id
    match_before = next(m for m in before if m.role_id == focus)
    match_after = next(m for m in after if m.role_id == focus)
    path_before = plan_pathway(pack, match_before, levels, data.weekly_hours, body.scenario, stored)
    path_after = plan_pathway(pack, match_after, levels, data.weekly_hours, body.scenario, tested)
    previous = {
        o.key: (
            stored.automation_share if o.kind == "occupation_share" else stored.task_automation
        ).get(o.key)
        for o in body.overrides
    }
    return EvidenceTestOut(
        label=TEST_LABEL,
        scenario=body.scenario,
        overrides=body.overrides,
        previous=previous,
        before=_ranking(before),
        after=_ranking(after),
        weights=_weights(before, after),
        pathway=PathwayChange(
            role_id=focus,
            title=match_before.title,
            before=[s.course.id for s in path_before.steps],
            after=[s.course.id for s in path_after.steps],
            titles={s.course.id: s.course.title for s in [*path_before.steps, *path_after.steps]},
            fit_after_before=path_before.fit_after,
            fit_after_after=path_after.fit_after,
        ),
    )
