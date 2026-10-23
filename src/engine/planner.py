"""Time-budgeted, scenario-robust learning path (Task A5, greedy version).

Model (PROJECT_PLAN §6; parameters in params.py):
  resources i: free courses, in-app practice bundles, confirmation check-ins; x_i ∈ {0, 1}
  budget:      Σ hours_i·x_i ≤ weekly_hours × H   (H = 6 weeks, or the person's timeframe, v2.2)
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
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from src.contract import (
    SCENARIOS,
    CompanyAssumptions,
    Course,
    PathPlan,
    PathStep,
    PathStepType,
    Profile,
    Scenario,
    SkillState,
)
from src.engine import params
from src.engine.catalogue import CaseInfo, Catalogue
from src.engine.recommend import DIRECTION_LABEL, credit
from src.engine.requirements import scenario_weights

PRACTICE_COST = "free"  # in-app synthetic practice cases


@dataclass(frozen=True)
class Resource:
    id: str  # unique per candidate (e.g. "practice:fx_conversion", "course_04")
    ref: str  # what the step points to: a case id or a course id
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


def _first_unseen(skill_id: str, mode: str, cases: Sequence[CaseInfo], taken: set[str]) -> str:
    """First case of `mode` practising the skill that is neither seen nor used by another step."""
    match = next(
        (c.id for c in cases if c.mode == mode and skill_id in c.skills and c.id not in taken),
        None,
    )
    if match:
        taken.add(match)
    return match or f"{mode}:{skill_id}"


def build_resources(
    skill_ids: Sequence[str],
    states: dict[str, SkillState],
    catalogue: Catalogue,
    cases: Sequence[CaseInfo],
    seen: set[str],
) -> list[Resource]:
    """Candidate resources for the role's skills (each case is the ref of at most one step)."""
    resources: list[Resource] = []
    taken = set(seen)
    for skill_id in skill_ids:
        info = catalogue.skills[skill_id]
        state = states.get(skill_id)
        if not info.practised or credit(state) >= 1:
            continue
        if needs_confirmation(state):
            resources.append(
                Resource(
                    id=f"checkin:{skill_id}",
                    ref=_first_unseen(skill_id, "checkin", cases, taken),
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
                id=f"practice:{skill_id}",
                ref=_first_unseen(skill_id, "practice", cases, taken),
                type="practice_case",
                title=f"{info.name}: {params.PRACTICE_BUNDLE_CASES} practice cases",
                hours=params.PRACTICE_BUNDLE_HOURS,
                gains={skill_id: params.RESOURCE_GAIN},
                because=f"{info.name} is {state.state if state else 'insufficient_evidence'}.",
            )
        )
    # Courses only target open gaps: not skills already demonstrated, and not skills waiting for
    # their confirmation check-in (more teaching would not produce the missing evidence).
    closed = {
        k for k in skill_ids if credit(states.get(k)) >= 1 or needs_confirmation(states.get(k))
    }
    learnable = [k for k in skill_ids if k not in closed]
    courses = [_course_resource(c, learnable) for c in catalogue.courses.values()]
    resources.extend(prefer_cheaper([c for c in courses if c.gains]))
    return [r for r in resources if r.gains]


def cost_tier(cost_label: str) -> int:
    """0 free, 1 low-cost, 2 paid or not stated (see params.py; never assume free)."""
    label = cost_label.strip().lower()
    if label.startswith(params.FREE_COST_PREFIX):
        return params.COST_TIER_FREE
    if label.startswith(params.LOW_COST_PREFIX):
        return params.COST_TIER_LOW
    return params.COST_TIER_PAID_OR_UNKNOWN


def prefer_cheaper(courses: Sequence[Resource]) -> list[Resource]:
    """Drop a course when another covers all of its skill gaps at a lower cost tier (rule 1)."""
    kept = []
    for course in courses:
        dominated = any(
            cost_tier(other.cost) < cost_tier(course.cost) and set(course.gains) <= set(other.gains)
            for other in courses
            if other.id != course.id
        )
        if not dominated:
            kept.append(course)
    return kept


def _course_resource(course: Course, skill_ids: Sequence[str]) -> Resource:
    covered = [k for k in course.skills if k in skill_ids]
    gains = {k: params.RESOURCE_GAIN for k in covered} if course.verified else {}
    return Resource(
        id=course.id,
        ref=course.id,
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
        best: tuple[tuple[float, float, int], list[Resource]] | None = None
        for resource in resources:
            if resource.id in chosen_ids:
                continue
            bundle = _with_prerequisites(resource, by_id, chosen_ids)
            hours = sum(r.hours for r in bundle)
            if spent + hours > budget_hours:
                continue
            new_worst, new_total = worst_case_gap(inputs, [*chosen, *bundle])
            # Rule 2: equal gap cut per hour → lower cost tier wins (negated: larger is better).
            key = (
                (worst - new_worst) / hours,
                (total - new_total) / hours,
                -cost_tier(resource.cost),
            )
            if key[1] <= params.MIN_GAP_IMPROVEMENT:
                continue
            if best is None or key > best[0]:
                best = (key, bundle)
        if best is None:
            return chosen
        chosen.extend(best[1])


Selector = Callable[[PlanInputs, Sequence[Resource], float], list[Resource]]


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


def ai_intro_first(ordered: Sequence[Resource], ai_comfort: int | None) -> list[Resource]:
    """Low AI comfort (≤ AI_COMFORT_LOW): move the shortest chosen AI-intro course to the front.

    Only reorders what the planner already chose (gap logic unchanged); the course's own
    prerequisites stay before it, and its reason says why it moved.
    """
    result = list(ordered)
    if ai_comfort is None or ai_comfort > params.AI_COMFORT_LOW:
        return result
    intros = [r for r in result if r.ref in params.AI_INTRO_COURSES]
    if not intros:
        return result
    intro = min(intros, key=lambda r: (r.hours, r.id))
    result.remove(intro)
    prereq_positions = [i for i, r in enumerate(result) if r.id in intro.prerequisites]
    position = max(prereq_positions) + 1 if prereq_positions else 0
    note = f"Placed first: you rated your comfort with AI tools {ai_comfort}/10."
    moved = replace(intro, because=f"{intro.because} {note}".strip())
    result.insert(position, moved)
    return result


def path_inputs(
    profile: Profile, plan: PathPlan, catalogue: Catalogue, role_from_direction: bool
) -> list[str]:
    """Plain-language lines naming the profile answers that shaped this path (empty if none)."""
    prefs = profile.preferences
    lines = []
    if prefs.timeframe_months is not None:
        lines.append(
            f"Timeframe {prefs.timeframe_months} months: planned within {plan.horizon_weeks} "
            f"weeks at {plan.weekly_hours:g} h/week."
        )
    if prefs.direction is not None and role_from_direction:
        title = catalogue.roles[plan.target_role_id].title
        lines.append(f"Direction: {DIRECTION_LABEL[prefs.direction]}, so the path is for {title}.")
    moved = plan.steps and plan.steps[0].ref in params.AI_INTRO_COURSES
    if moved and prefs.ai_comfort is not None and prefs.ai_comfort <= params.AI_COMFORT_LOW:
        lines.append(f"AI comfort {prefs.ai_comfort}/10: an AI-intro course comes first.")
    return lines


def plan_inputs(
    role_id: str,
    states: dict[str, SkillState],
    catalogue: Catalogue,
    assumptions: CompanyAssumptions,
) -> PlanInputs:
    role = catalogue.roles[role_id]
    skill_types = catalogue.skill_types
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
        ref=resource.ref,
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
    selector: "Selector | None" = None,
    horizon_weeks: int = params.PLAN_HORIZON_WEEKS,
    ai_comfort: int | None = None,
) -> PathPlan:
    """The robust path for one employee and target role (contract PathPlan).

    `selector` picks the resources: greedy_select by default, or planner_cpsat.cpsat_select.
    """
    by_skill = {s.skill_id: s for s in states}
    inputs = plan_inputs(role_id, by_skill, catalogue, assumptions)
    role_skills = [s.skill_id for s in catalogue.roles[role_id].skills]
    resources = build_resources(role_skills, by_skill, catalogue, cases, seen_case_ids)
    budget = weekly_hours * horizon_weeks
    chosen = ai_intro_first(
        order_steps(inputs, (selector or greedy_select)(inputs, resources, budget)), ai_comfort
    )
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
        horizon_weeks=horizon_weeks,
    )
