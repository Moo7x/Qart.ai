"""Compare learning plans for one role within the same time budget (PLAN §4.6).

Budget = weekly hours × PLAN_BUDGET_WEEKS. Three plans, all scored by the same rules as the
planner (course gains are the declared estimates in src/params.py, not measured learning):

* greedy  – today's planner order (essentials first, shortest useful course each), cut where the
            budget runs out: the baseline.
* best    – exact search over every prerequisite-complete set of relevant courses that fits the
            budget, for the chosen scenario. Objective, in order: most essential requirements
            reached, then highest projected fit, then fewest hours.
* robust  – the same search, maximising the lower of the two scenarios' projected fits: first
            steps that hold up whichever adoption scenario happens.
The search is exhaustive (a proven optimum for this objective and catalogue) when the relevant
courses are at most PLAN_MAX_EXACT_COURSES; otherwise only the greedy plan is reported.
"""

from collections.abc import Mapping
from itertools import combinations
from typing import Any

from src import params
from src.match.engine import Evidence, RoleMatch, Scenario, score_role
from src.pack import Course, Pack
from src.pathway.planner import MINUTES_PER_HOUR, _level_after, plan_pathway

LEVEL_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
Levels = Mapping[str, int | None]


def _ordered(pack: Pack, ids: set[str]) -> list[Course]:
    """Prerequisites before the courses that need them, then easier and shorter first."""
    out: list[Course] = []

    def add(course: Course) -> None:
        if course in out:
            return
        for req in course.requires:
            add(pack.courses[req])
        out.append(course)

    for course in sorted(
        (pack.courses[i] for i in ids), key=lambda c: (LEVEL_ORDER[c.level], c.minutes, c.id)
    ):
        add(course)
    return out


def _closed(pack: Pack, ids: set[str]) -> bool:
    return all(req in ids for i in ids for req in pack.courses[i].requires)


def simulate(pack: Pack, match: RoleMatch, levels: Levels, ids: set[str]) -> dict[str, int]:
    """Levels after taking these courses, by the planner's gain rules."""
    needed = {r.skill: r.required for r in match.requirements}
    current = {k: (v or 0) for k, v in levels.items()}
    for course in _ordered(pack, ids):
        for skill in course.covers:
            if skill in needed:
                current[skill] = _level_after(course, current.get(skill, 0), needed[skill])
    return current


def _hours(pack: Pack, ids: set[str]) -> float:
    return round(sum(pack.courses[i].minutes for i in ids) / MINUTES_PER_HOUR, 1)


def _evaluate(
    pack: Pack, match: RoleMatch, levels: Levels, ids: set[str], evidence: Evidence
) -> dict[str, Any]:
    role = pack.destination_roles[match.role_id]
    after = simulate(pack, match, levels, ids)
    fits = {s: score_role(pack, role, after, s, evidence) for s in ("moderate", "fast")}
    essentials = [r for r in match.requirements if r.essential]
    reached = sum(after.get(r.skill, 0) >= r.required for r in essentials)
    return {
        "course_ids": [c.id for c in _ordered(pack, ids)],
        "courses": [
            {"id": c.id, "title": c.title, "url": c.url, "hours": round(c.minutes / 60, 1)}
            for c in _ordered(pack, ids)
        ],
        "hours": _hours(pack, ids),
        "fit_after": {s: m.fit for s, m in fits.items()},
        "essentials_reached": reached,
        "essentials_total": len(essentials),
    }


def _relevant(pack: Pack, match: RoleMatch) -> set[str]:
    gaps = {r.skill for r in match.requirements if (r.claimed or 0) < r.required}
    ids: set[str] = set()
    stack = [c.id for skill in gaps for c in pack.courses_for(skill)]
    while stack:
        course = stack.pop()
        if course not in ids:
            ids.add(course)
            stack += pack.courses[course].requires
    return ids


def compare_plans(
    pack: Pack,
    match: RoleMatch,
    levels: Levels,
    weekly_hours: float,
    scenario: Scenario,
    evidence: Evidence,
) -> dict[str, Any]:
    budget = round(weekly_hours * params.PLAN_BUDGET_WEEKS, 1)
    full = plan_pathway(pack, match, levels, weekly_hours, scenario, evidence)
    greedy: set[str] = set()
    for step in full.steps:  # the planner's own order, cut at the budget
        if _hours(pack, greedy | {step.course.id}) > budget:
            break
        greedy.add(step.course.id)
    plans = {"greedy": _evaluate(pack, match, levels, greedy, evidence)}
    relevant = sorted(_relevant(pack, match))
    exact = len(relevant) <= params.PLAN_MAX_EXACT_COURSES
    if exact:
        best_key: tuple[float, ...] | None = None
        robust_key: tuple[float, ...] | None = None
        best_ids: set[str] = set()
        robust_ids: set[str] = set()
        for size in range(len(relevant) + 1):
            for combo in combinations(relevant, size):
                ids = set(combo)
                if not _closed(pack, ids) or _hours(pack, ids) > budget:
                    continue
                result = _evaluate(pack, match, levels, ids, evidence)
                fits = result["fit_after"]
                key = (result["essentials_reached"], fits[scenario], -result["hours"])
                worst = min(fits.values())
                rkey = (result["essentials_reached"], worst, -result["hours"])
                if best_key is None or key > best_key:
                    best_key, best_ids = key, ids
                if robust_key is None or rkey > robust_key:
                    robust_key, robust_ids = rkey, ids
        plans["best"] = _evaluate(pack, match, levels, best_ids, evidence)
        plans["robust"] = _evaluate(pack, match, levels, robust_ids, evidence)
    return {
        "role_id": match.role_id,
        "scenario": scenario,
        "budget_hours": budget,
        "budget_weeks": params.PLAN_BUDGET_WEEKS,
        "fit_now": match.fit,
        "relevant_courses": len(relevant),
        "exact": exact,
        "plans": plans,
        "note": (
            "Exhaustive search: 'best' and 'robust' are optimal for the stated objective."
            if exact
            else "Too many relevant courses for exhaustive search; only the greedy plan is shown."
        ),
    }
