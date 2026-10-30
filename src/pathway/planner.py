"""Plan the steps from a person's current levels to a chosen destination role.

Rules (all explainable, no optimiser needed for a catalogue this size; docs/PHASE2_PLAN.md §8 B4):
1. Gaps are the role's requirements the person does not meet yet: essentials first, then by weight.
2. Study: for each gap, verified courses covering the skill are added shortest first (after their
   prerequisites) until the material reaches the level study can give, `study_level`: level 1
   from LEVEL1_MIN_HOURS of material, level 2 from LEVEL2_MIN_HOURS including a hands-on item,
   never above STUDY_MAX_LEVEL or the level the role needs. Courses that cannot change that level
   are not added. A gap study cannot bring to its study target is "partly covered"; one with no
   verified course is listed as having no verified free course yet.
3. Practice: a requirement above STUDY_MAX_LEVEL gets one practice step per level above it
   (data/packs/gbs_fa/practice.yaml), in sequence after that skill's study, as a week range
   (estimate). Practice tasks are suggestions to agree with a manager, not courses.
4. Study steps are laid out week by week at the person's weekly hours; a course is taken once.
5. Every step names the skills it raises and the SDG targets those skills serve, with the reason.
Fits after the plan are estimates: after study assumes the person finishes the courses; after
practice also assumes the practice targets are reached. Both are ranges by the C2 rule, with
planned levels counted as unevidenced (src/match/decision.py fit_range).
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from src import params
from src.journey.store import SkillClaim
from src.match.decision import fit_range
from src.match.engine import Evidence, RoleMatch, Scenario, score_role
from src.pack import Course, Pack, SdgLink
from src.pathway.practice import load_practice

MINUTES_PER_HOUR = 60
AI_BASICS_REASON = (
    "AI basics come first for everyone: adapting to AI starts with knowing how to use it safely."
)
FREE_SHARE_BASIS = "Every verified course in the catalogue is free to study."


@dataclass(frozen=True)
class SkillGain:
    skill: str
    skill_name: str
    before: int
    after: int


@dataclass(frozen=True)
class StepSdg:
    target: str
    title: str
    how: str


@dataclass
class Step:
    order: int
    course: Course
    hours: float
    week_start: int
    week_end: int
    gains: list[SkillGain]
    sdgs: list[StepSdg]
    prerequisite_for: list[str] = field(default_factory=list)  # course ids that need this one
    # C3 fields (docs/PHASE2_PLAN.md §4): the same shape as a practice step.
    kind: str = "course"
    id: str = ""
    skill: str = ""  # the gap this course was added for
    target_level: int = 0
    time: dict[str, Any] = field(default_factory=dict)
    locked: bool = False
    unlock: str | None = None
    done: bool = False


@dataclass
class PracticeStep:
    order: int
    kind: str
    id: str  # "practice:<skill>:<level>"
    skill: str
    skill_name: str
    target_level: int
    text: str
    show_by: str
    time: dict[str, Any]
    week_start: dict[str, int]  # after the skill's study steps, as a range
    basis: list[dict[str, str]]
    locked: bool = False
    unlock: str | None = "study_done"
    # open · done (the claim reached the target) · skipped ("continue anyway"), each labelled.
    status: str = "open"
    status_label: str = ""


@dataclass
class Pathway:
    role_id: str
    role_title: str
    weekly_hours: float
    steps: list[Step]
    total_hours: float
    weeks: int
    uncovered: list[str]  # skill names with no verified free course yet
    partly_covered: list[str]  # skill names study raises, but not to the level study can give
    essentials_unmet: list[str]  # essential skills still below level after the study steps
    fit_before: float
    fit_after: float  # after the study steps (estimate)
    sdg_summary: dict[str, list[str]]  # target -> mechanisms
    pathway_sdgs: list[SdgLink]
    # C3 totals.
    practice_steps: list[PracticeStep] = field(default_factory=list)
    study_hours: float = 0.0
    practice_weeks: dict[str, int] = field(default_factory=dict)
    fit_after_study: dict[str, Any] = field(default_factory=dict)
    fit_after_practice: dict[str, Any] = field(default_factory=dict)
    free_share: float | None = None  # share of study hours in free courses; None = no study
    free_share_basis: str = FREE_SHARE_BASIS
    ai_basics: dict[str, Any] = field(default_factory=dict)
    study_levels: dict[str, int] = field(default_factory=dict)  # skill -> level after study


def study_level(hours: float, hands_on: bool) -> int:
    """Level a body of material can give a skill: the B4 rule, before any cap."""
    if hours >= params.LEVEL2_MIN_HOURS and hands_on:
        return 2
    if hours >= params.LEVEL1_MIN_HOURS:
        return 1
    return 0


def level_after_study(courses: list[Course], skill: str, current: int, required: int) -> int:
    """A skill's level after studying these courses: never lower, never above what study gives."""
    material = [c for c in courses if skill in c.covers]
    hours = sum(c.minutes for c in material) / MINUTES_PER_HOUR
    reached = study_level(hours, any(c.hands_on for c in material))
    return max(current, min(reached, params.STUDY_MAX_LEVEL, required))


def _with_prerequisites(pack: Pack, course: Course, chosen: list[Course]) -> list[Course]:
    """The course preceded by any prerequisites not chosen yet (depth first)."""
    out: list[Course] = []
    for prereq_id in course.requires:
        prereq = pack.courses[prereq_id]
        if prereq not in chosen and prereq not in out:
            out += _with_prerequisites(pack, prereq, chosen + out)
    return [*out, course]


def _step_sdgs(pack: Pack, skills: list[str]) -> list[StepSdg]:
    """SDG targets of the gap skills a step's material serves (it counts toward their level)."""
    seen: dict[str, StepSdg] = {}
    for skill in skills:
        for link in pack.sdg.skill_kinds[pack.skills[skill].kind]:
            if link.target not in seen:
                target = pack.sdg.targets[link.target]
                seen[link.target] = StepSdg(link.target, target.title, link.how)
    return list(seen.values())


def _planned_claims(
    claims: Mapping[str, SkillClaim] | None,
    levels: Mapping[str, int | None],
    planned: Mapping[str, int],
) -> dict[str, SkillClaim]:
    """Today's claims (evidenced unless told otherwise), with planned levels as unevidenced."""
    out = (
        dict(claims)
        if claims is not None
        else {
            k: SkillClaim(level=v, evidence="claimed", source="cv")
            for k, v in levels.items()
            if v is not None
        }
    )
    for skill, level in planned.items():
        if level != levels.get(skill):
            out[skill] = SkillClaim(level=level, source="self")
    return out


def plan_pathway(
    pack: Pack,
    match: RoleMatch,
    levels: Mapping[str, int | None],
    weekly_hours: float,
    scenario: Scenario,
    evidence: Evidence,
    claims: Mapping[str, SkillClaim] | None = None,
) -> Pathway:
    if weekly_hours <= 0:
        raise ValueError("weekly hours must be positive")
    role = pack.destination_roles[match.role_id]
    gaps = [r for r in match.requirements if (r.claimed or 0) < r.required]
    gaps.sort(key=lambda r: (not r.essential, -r.weight))
    needed = {r.skill: r.required for r in match.requirements}
    start = {k: (v or 0) for k, v in levels.items()}
    current = dict(start)
    chosen: list[Course] = []
    reason: dict[str, str] = {}  # course id -> the gap it was added for

    def raise_by(courses: list[Course], skill: str) -> int:
        return level_after_study(courses, skill, start.get(skill, 0), needed[skill])

    uncovered: list[str] = []
    partly: list[str] = []
    for gap in gaps:
        options = pack.courses_for(gap.skill)
        if not options:
            uncovered.append(gap.skill_name)
            continue
        target = min(gap.required, params.STUDY_MAX_LEVEL)
        # The most study can give with every course available; courses beyond it add nothing.
        reachable = raise_by(chosen + [c for c in options if c not in chosen], gap.skill)
        for course in sorted(options, key=lambda c: (c.minutes, c.id)):
            if current.get(gap.skill, 0) >= reachable:
                break
            if course in chosen:
                continue
            for item in _with_prerequisites(pack, course, chosen):
                if item not in chosen:
                    chosen.append(item)
                    reason.setdefault(item.id, gap.skill)
            for skill in needed:
                current[skill] = raise_by(chosen, skill)
        if current.get(gap.skill, 0) < target:
            partly.append(gap.skill_name)

    gap_skills = {g.skill for g in gaps}
    steps: list[Step] = []
    elapsed = 0.0
    taken: list[Course] = []
    study_end: dict[str, int] = {}
    for order, course in enumerate(chosen, start=1):
        before = {s: raise_by(taken, s) for s in course.covers if s in needed}
        taken.append(course)
        gains = [
            SkillGain(s, pack.skills[s].name, b, reached)
            for s, b in before.items()
            if (reached := raise_by(taken, s)) > b
        ]
        hours = round(course.minutes / MINUTES_PER_HOUR, 1)
        week_start = math.floor(elapsed / weekly_hours) + 1
        elapsed += hours
        week_end = max(week_start, math.ceil(elapsed / weekly_hours))
        for s in course.covers:
            if s in needed:
                study_end[s] = week_end
        skill = reason.get(course.id, gains[0].skill if gains else "")
        steps.append(
            Step(
                order,
                course,
                hours,
                week_start,
                week_end,
                gains,
                _step_sdgs(pack, [s for s in course.covers if s in gap_skills]),
                [c.id for c in chosen if course.id in c.requires],
                kind="course",
                id=course.id,
                skill=skill,
                target_level=raise_by(taken, skill) if skill in needed else 0,
                time={
                    "value": hours,
                    "unit": "hours",
                    "basis": course.time_basis,
                    "low": None,
                    "high": None,
                },
                unlock="previous_step" if order > 1 else None,
            )
        )

    practice_steps = _practice_steps(pack, gaps, current, study_end, len(steps))
    after_study = {**{k: v for k, v in levels.items()}, **current}
    after_practice = {**after_study, **{p.skill: p.target_level for p in practice_steps}}
    after = score_role(pack, role, after_study, scenario, evidence)
    practiced = score_role(pack, role, after_practice, scenario, evidence)
    summary: dict[str, list[str]] = {}
    for step in steps:
        for sdg in step.sdgs:
            summary.setdefault(sdg.target, [])
            if sdg.how not in summary[sdg.target]:
                summary[sdg.target].append(sdg.how)
    for link in [*pack.sdg.pathway, *pack.sdg.destination]:
        summary.setdefault(link.target, []).append(link.how)
    total = round(sum(s.hours for s in steps), 1)
    planned_study = {k: v for k, v in after_study.items() if v is not None}
    planned_practice = {k: v for k, v in after_practice.items() if v is not None}
    return Pathway(
        role_id=match.role_id,
        role_title=match.title,
        weekly_hours=weekly_hours,
        steps=steps,
        total_hours=total,
        weeks=steps[-1].week_end if steps else 0,
        uncovered=uncovered,
        partly_covered=partly,
        essentials_unmet=after.essential_gaps,
        fit_before=match.fit,
        fit_after=after.fit,
        sdg_summary=summary,
        pathway_sdgs=[*pack.sdg.pathway, *pack.sdg.destination],
        practice_steps=practice_steps,
        study_hours=total,
        practice_weeks={
            "low": sum(p.time["low"] for p in practice_steps),
            "high": sum(p.time["high"] for p in practice_steps),
        },
        fit_after_study=_range(
            pack,
            after,
            after_study,
            scenario,
            evidence,
            _planned_claims(claims, levels, planned_study),
        ),
        fit_after_practice=_range(
            pack,
            practiced,
            after_practice,
            scenario,
            evidence,
            _planned_claims(claims, levels, planned_practice),
        ),
        free_share=1.0 if total else None,
        ai_basics={"shown": True, "reason": AI_BASICS_REASON},
        study_levels={g.skill: current.get(g.skill, 0) for g in gaps},
    )


def apply_progress(
    path: Pathway,
    done: list[str],
    skipped: list[str],
    claims: Mapping[str, SkillClaim],
) -> Pathway:
    """Lock and complete steps from the person's own records (B4 unlocking rules).

    A course step unlocks when the step before it is done. A practice step unlocks when the
    study steps for its skill are done, and is complete when the skill's claim reaches its
    target: "checked" through an accepted progress check, "self-rated" otherwise. A step passed
    with "continue anyway" is skipped, labelled, and never counted as done.
    """
    finished = set(done)
    for i, step in enumerate(path.steps):
        step.done = step.course.id in finished
        step.locked = i > 0 and not path.steps[i - 1].done
    for p in path.practice_steps:
        study = [s for s in path.steps if s.skill == p.skill or p.skill in s.course.covers]
        p.locked = not all(s.done for s in study)
        claim = claims.get(p.skill)
        if claim is not None and (claim.level or 0) >= p.target_level:
            p.status = "done"
            p.status_label = "checked" if claim.source == "agent_check" else "self-rated"
            p.locked = False
        elif p.id in skipped:
            p.status, p.status_label = "skipped", "continued anyway, not done"
    return path


def practice_step_id(skill: str, level: int) -> str:
    return f"practice:{skill}:{level}"


def _range(
    pack: Pack,
    match: RoleMatch,
    levels: Mapping[str, int | None],
    scenario: Scenario,
    evidence: Evidence,
    claims: Mapping[str, SkillClaim],
) -> dict[str, Any]:
    found = fit_range(pack, match, levels, scenario, evidence, claims)
    return {"low": found["low"], "high": found["high"], "kind": "estimate"}


def _practice_steps(
    pack: Pack,
    gaps: list[Any],
    after_study: Mapping[str, int],
    study_end: Mapping[str, int],
    first_order: int,
) -> list[PracticeStep]:
    """One practice step per level above STUDY_MAX_LEVEL, in sequence after the skill's study."""
    practice = load_practice()
    out: list[PracticeStep] = []
    for gap in gaps:
        start = max(params.STUDY_MAX_LEVEL, after_study.get(gap.skill, 0))
        low = high = study_end.get(gap.skill, 0)
        for level in range(start + 1, gap.required + 1):
            task = practice.task(gap.skill, level)
            if task is None:
                continue
            out.append(
                PracticeStep(
                    order=first_order + len(out) + 1,
                    kind="practice",
                    id=practice_step_id(gap.skill, level),
                    skill=gap.skill,
                    skill_name=gap.skill_name,
                    target_level=level,
                    text=task.text,
                    show_by=task.show_by,
                    time={
                        "value": task.weeks_low,
                        "unit": "weeks",
                        "basis": "practice_estimate",
                        "low": task.weeks_low,
                        "high": task.weeks_high,
                    },
                    week_start={"low": low + 1, "high": high + 1},
                    basis=[b.model_dump() for b in task.basis],
                )
            )
            low += task.weeks_low
            high += task.weeks_high
    return out
