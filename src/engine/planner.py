"""Time-budgeted, scenario-robust learning path (Task A5, greedy version).

Model (PROJECT_PLAN §6; parameters in params.py):
  resources i: free courses, in-app practice bundles, confirmation check-ins; x_i ∈ {0, 1}
  budget:      Σ hours_i·x_i ≤ weekly_hours × 6
  prerequisites: a course is only chosen together with its prerequisites
  gap:         g_{sc,k} = max(0, 1 − credit(state_k) − Σ_i gain_{i,k}·x_i)
               gain = 0.3 per covering course or bundle (ASSUMPTION: coverage is not demonstrated
               skill until new case evidence arrives); a confirmation check-in's expected gain is
               the remaining 0.5 (it can turn "1 of 2" into "demonstrated")
  objective:   minimise max over scenarios of Σ_k w_{sc,k}·g_{sc,k}   (robust path)
Greedy: repeatedly add the affordable resource (with its missing prerequisites) that cuts the
worst-case gap most per hour (ties: total gap cut per hour, then id); stop when nothing helps.
A skill at "observed with help, 1 of 2 independent successes" gets ONE confirmation check-in and
no learning module: more teaching would not produce the missing evidence.
"""

import math
from collections.abc import Sequence
from dataclasses import dataclass

from src.contract import (
    SCENARIOS,
    CompanyAssumptions,
    Course,
    PathPlan,
    PathStep,
    PathStepType,
    Scenario,
    SkillState,
)
from src.engine import params
from src.engine.catalogue import CaseInfo, Catalogue
from src.engine.recommend import credit
from src.engine.requirements import scenario_weights

PRACTICE_COST = "free"  # in-app synthetic practice cases


@dataclass(frozen=True)
class Resource:
    id: str
    type: PathStepType
    title: str
    hours: float
    gains: dict[str, float]
    prerequisites: tuple[str, ...] = ()
    url: str | None = None
    retrieved: str | None = None
    cost: str = PRACTICE_COST
    because: str = ""


@dataclass(frozen=True)
class PlanInputs:
    weights: dict[Scenario, dict[str, float]]
    remaining: dict[str, float]  # 1 − credit(state) per skill in the role


def needs_confirmation(state: SkillState | None) -> bool:
    return (
        state is not None
        and state.state == "observed_with_help"
        and 0 < state.independent_successes < params.REQUIRED_INDEPENDENT_SUCCESSES
    )


def _first_unseen(skill_id: str, mode: str, cases: Sequence[CaseInfo], seen: set[str]) -> str:
    match = next(
        (c.id for c in cases if c.mode == mode and skill_id in c.skills and c.id not in seen), None
    )
    return match or f"{mode}:{skill_id}"


def build_resources(
    skill_ids: Sequence[str],
    states: dict[str, SkillState],
    catalogue: Catalogue,
    cases: Sequence[CaseInfo],
    seen: set[str],
) -> list[Resource]:
    """Candidate resources for the role's skills."""
    resources: list[Resource] = []
    for skill_id in skill_ids:
        info = catalogue.skills[skill_id]
        state = states.get(skill_id)
        if not info.practised or credit(state) >= 1:
            continue
        if needs_confirmation(state):
            ref = _first_unseen(skill_id, "checkin", cases, seen)
            resources.append(
                Resource(
                    id=ref,
                    type="checkin",
                    title=f"Confirmation check-in: {info.name} (later session)",
                    hours=params.CHECKIN_HOURS,
                    gains={skill_id: params.CHECKIN_GAIN},
                    because=(
                        f"Replaces the {info.name} practice module: you have 1 of "
                        f"{params.REQUIRED_INDEPENDENT_SUCCESSES} independent successes; one more "
                        "no-help success in a separate session confirms it."
                    ),
                )
            )
            continue
        resources.append(
            Resource(
                id=_first_unseen(skill_id, "practice", cases, seen),
                type="practice_case",
                title=f"{info.name}: {params.PRACTICE_BUNDLE_CASES} practice cases",
                hours=params.PRACTICE_BUNDLE_HOURS,
                gains={skill_id: params.RESOURCE_GAIN},
                because=f"{info.name} is {state.state if state else 'insufficient_evidence'}.",
            )
        )
    resources.extend(_course_resource(c, skill_ids) for c in catalogue.courses.values())
    return [r for r in resources if r.gains]


def _course_resource(course: Course, skill_ids: Sequence[str]) -> Resource:
    covered = [k for k in course.skills if k in skill_ids]
    gains = {k: params.RESOURCE_GAIN for k in covered} if course.verified else {}
    return Resource(
        id=course.id,
        type="course",
        title=f"{course.title} ({course.provider})",
        hours=course.hours,
        gains=gains,
        prerequisites=tuple(course.prerequisites),
        url=course.url,
        retrieved=course.retrieved,
        cost=course.cost,
        because=(
            f"Covers {', '.join(covered)} (assumed gap reduction {params.RESOURCE_GAIN} per skill "
            "until new case evidence confirms it)."
        ),
    )


def worst_case_gap(inputs: PlanInputs, chosen: Sequence[Resource]) -> tuple[float, float]:
    """(max over scenarios, sum over scenarios) of Σ_k w·g after the chosen resources."""
    gained: dict[str, float] = {}
    for resource in chosen:
        for skill_id, gain in resource.gains.items():
            gained[skill_id] = gained.get(skill_id, 0.0) + gain
    per_scenario = [
        sum(
            w * max(0.0, inputs.remaining.get(k, 0.0) - gained.get(k, 0.0))
            for k, w in inputs.weights[sc].items()
        )
        for sc in SCENARIOS
    ]
    return max(per_scenario), sum(per_scenario)


def _with_prerequisites(
    resource: Resource, by_id: dict[str, Resource], chosen_ids: set[str]
) -> list[Resource]:
    bundle: list[Resource] = []
    stack = [resource]
    while stack:
        item = stack.pop()
        if item.id in chosen_ids or item in bundle:
            continue
        bundle.append(item)
        stack.extend(by_id[p] for p in item.prerequisites if p in by_id)
    return bundle


def greedy_select(
    inputs: PlanInputs, resources: Sequence[Resource], budget_hours: float
) -> list[Resource]:
    by_id = {r.id: r for r in resources}
    chosen: list[Resource] = []
    while True:
        chosen_ids = {r.id for r in chosen}
        spent = sum(r.hours for r in chosen)
        worst, total = worst_case_gap(inputs, chosen)
        best: tuple[tuple[float, float, str], list[Resource]] | None = None
        for resource in resources:
            if resource.id in chosen_ids:
                continue
            bundle = _with_prerequisites(resource, by_id, chosen_ids)
            hours = sum(r.hours for r in bundle)
            if spent + hours > budget_hours:
                continue
            new_worst, new_total = worst_case_gap(inputs, [*chosen, *bundle])
            key = ((worst - new_worst) / hours, (total - new_total) / hours, resource.id)
            if key[1] <= params.MIN_GAP_IMPROVEMENT:
                continue
            if best is None or (key[0], key[1]) > (best[0][0], best[0][1]):
                best = (key, bundle)
        if best is None:
            return chosen
        chosen.extend(best[1])


def order_steps(inputs: PlanInputs, chosen: Sequence[Resource]) -> list[Resource]:
    """Prerequisites first, then the largest standalone worst-case gap cut per hour."""
    start, _ = worst_case_gap(inputs, [])

    def ratio(r: Resource) -> float:
        return (start - worst_case_gap(inputs, [r])[0]) / r.hours

    remaining = list(chosen)
    ordered: list[Resource] = []
    while remaining:
        placed = {r.id for r in ordered}
        ready = [r for r in remaining if all(p in placed for p in r.prerequisites)] or remaining
        nxt = max(ready, key=lambda r: (ratio(r), r.type == "checkin", r.id))
        ordered.append(nxt)
        remaining.remove(nxt)
    return ordered


def plan_inputs(
    role_id: str,
    states: dict[str, SkillState],
    catalogue: Catalogue,
    assumptions: CompanyAssumptions,
) -> PlanInputs:
    role = catalogue.roles[role_id]
    skill_types = {k: s.type for k, s in catalogue.skills.items()}
    weights = {
        sc: scenario_weights(role, sc, assumptions, skill_types).scenario for sc in SCENARIOS
    }
    remaining = {s.skill_id: 1 - credit(states.get(s.skill_id)) for s in role.skills}
    return PlanInputs(weights=weights, remaining=remaining)


def _sdg_targets(skill_ids: Sequence[str], catalogue: Catalogue) -> list[str]:
    targets = {t for k in skill_ids for t in catalogue.sdg.skills[k].targets}
    return sorted(targets)


def _to_step(order: int, resource: Resource, catalogue: Catalogue) -> PathStep:
    skills = list(resource.gains)
    return PathStep(
        order=order,
        type=resource.type,
        ref=resource.id,
        title=resource.title,
        hours=resource.hours,
        skills=skills,
        cost=resource.cost,
        url=resource.url,
        retrieved=resource.retrieved,
        sdg_targets=_sdg_targets(skills, catalogue),
        because=resource.because,
    )


def plan_path(
    user_id: str,
    role_id: str,
    weekly_hours: float,
    states: Sequence[SkillState],
    catalogue: Catalogue,
    assumptions: CompanyAssumptions,
    cases: Sequence[CaseInfo],
    seen_case_ids: set[str],
) -> PathPlan:
    """The robust path for one employee and target role (contract PathPlan)."""
    by_skill = {s.skill_id: s for s in states}
    inputs = plan_inputs(role_id, by_skill, catalogue, assumptions)
    role_skills = [s.skill_id for s in catalogue.roles[role_id].skills]
    resources = build_resources(role_skills, by_skill, catalogue, cases, seen_case_ids)
    budget = weekly_hours * params.PLAN_HORIZON_WEEKS
    chosen = order_steps(inputs, greedy_select(inputs, resources, budget))
    total = sum(r.hours for r in chosen)
    return PathPlan(
        user_id=user_id,
        target_role_id=role_id,
        weekly_hours=weekly_hours,
        robust_across=list(SCENARIOS),
        steps=[_to_step(i, r, catalogue) for i, r in enumerate(chosen, start=1)],
        total_hours=round(total, params.SCORE_DECIMALS),
        weeks=math.ceil(total / weekly_hours) if total else 0,
        worst_case_gap=round(worst_case_gap(inputs, chosen)[0], params.SCORE_DECIMALS),
    )
