"""Change test: recompute roles, weights and pathway with test evidence values; nothing is saved.

docs/PHASE2_PLAN.md A3 and contract C7. Owner: A (p2-ai-experience). Registered in
src/app.py in Stage 0; routes are added here only.

A judge can ask "change the trend data now: what should change?". This route answers it with the
real engine: the stored evidence is copied, one or more observed AI-use shares are replaced by
test values, and the unchanged `rank_roles`, `score_role` and `plan_pathway` run on both. Stored
observations, the profile and the accepted journey are never touched.
"""

from dataclasses import replace
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.api.journey import require_person
from src.forecast.industry import Overrides
from src.match.engine import Evidence, RoleMatch, Scenario
from src.match.outlook import MAJOR_GROUP
from src.pack import Pack

router = APIRouter(prefix="/api/profiles/{profile_id}")

GROUP_CHANGE_LIMIT = 5.0  # points; a 5-point move in two years would be far beyond any DOSM year
TEST_LABEL = "Test value, not real data"
MAX_OVERRIDES = 10
WEIGHT_DECIMALS = 3


class Override(BaseModel):
    # occupation_share / task_share: % of AI use that is automation-style (0-100), for an O*NET-SOC
    # code or an O*NET task id. group_change: a DOSM job group's forecast change in its share of
    # employees, in points (GROUP_CHANGE_LIMIT either way), keyed by group (e.g. "clerical").
    kind: Literal["occupation_share", "task_share", "group_change"]
    key: str = Field(min_length=1, max_length=32)
    value: float = Field(ge=-100, le=100)

    @model_validator(mode="after")
    def _range(self) -> "Override":
        if self.kind == "group_change":
            if abs(self.value) > GROUP_CHANGE_LIMIT:
                raise ValueError(f"group_change must be within ±{GROUP_CHANGE_LIMIT} points")
        elif not 0 <= self.value <= 100:
            raise ValueError("an AI-use share must be between 0 and 100")
        return self


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


class CategoryChange(BaseModel):
    """A role whose Qart forecast category moves under the test values."""

    role_id: str
    title: str
    before: str
    after: str
    current_job: bool  # the person's own job


class EvidenceTestOut(BaseModel):
    label: str
    scenario: Scenario
    overrides: list[Override]
    previous: dict[str, float | None]  # the stored value each override replaced (None = missing)
    before: Ranking
    after: Ranking
    weights: list[WeightChange]
    pathway: PathwayChange | None
    forecast: list[CategoryChange] = []  # Qart forecast categories that changed


def _check_keys(pack: Pack, overrides: list[Override]) -> None:
    socs = {role.soc for role in pack.destination_roles.values()}
    socs |= {role.soc for role in pack.current_roles.values()}
    tasks = pack.task_ids()
    groups = set(MAJOR_GROUP.values())
    unknown = [
        o.key
        for o in overrides
        if (o.kind == "occupation_share" and o.key not in socs)
        or (o.kind == "task_share" and o.key not in tasks)
        or (o.kind == "group_change" and o.key not in groups)
    ]
    if unknown:
        raise HTTPException(status_code=422, detail=f"unknown keys: {', '.join(unknown)}")


def apply_overrides(evidence: Evidence, overrides: list[Override]) -> Evidence:
    """A copy of the evidence with the test values in place; the original is not changed."""
    occupation = dict(evidence.automation_share)
    task = dict(evidence.task_automation)
    for o in overrides:
        if o.kind == "occupation_share":
            occupation[o.key] = o.value
        elif o.kind == "task_share":
            task[o.key] = o.value
    return replace(evidence, automation_share=occupation, task_automation=task)


def forecast_overrides(overrides: list[Override]) -> Overrides:
    """The same test values for the Qart forecast: AI use on the tasks, and job-group trends."""
    return Overrides(
        occupation_use={o.key: o.value for o in overrides if o.kind == "occupation_share"},
        task_use={o.key: o.value for o in overrides if o.kind == "task_share"},
        group_change={o.key: o.value for o in overrides if o.kind == "group_change"},
    )


def category_changes(
    before: dict[str, dict[str, Any]], after: dict[str, dict[str, Any]], current: str | None
) -> list[CategoryChange]:
    return [
        CategoryChange(
            role_id=role_id,
            title=row["title"],
            before=row["label"],
            after=after[role_id]["label"],
            current_job=role_id == current,
        )
        for role_id, row in before.items()
        if role_id in after and after[role_id]["category"] != row["category"]
    ]


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
    person = require_person(engine, profile_id)
    pack = person.pack
    _check_keys(pack, body.overrides)
    stored = person.evidence
    tested = apply_overrides(stored, body.overrides)
    test_forecast = forecast_overrides(body.overrides)
    before = person.rank(body.scenario, stored)
    after = person.rank(body.scenario, tested, test_forecast)
    changed = category_changes(
        person.forecasts(body.scenario),
        person.forecasts(body.scenario, test_forecast),
        person.data.current_role,
    )
    focus = person.destination or before[0].role_id
    match_before = next(m for m in before if m.role_id == focus)
    match_after = next(m for m in after if m.role_id == focus)
    path_before = person.plan(match_before, body.scenario, stored)
    path_after = person.plan(match_after, body.scenario, tested)
    demand = {
        r["demand"]["group"]: r["demand"].get("change_pp")
        for r in person.forecasts(body.scenario).values()
    }
    previous = {
        o.key: (
            demand.get(o.key)
            if o.kind == "group_change"
            else (
                stored.automation_share if o.kind == "occupation_share" else stored.task_automation
            ).get(o.key)
        )
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
        forecast=changed,
    )
