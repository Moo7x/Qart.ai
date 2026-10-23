"""Plan the steps from a person's current levels to a chosen destination role.

Rules (all explainable, no optimiser needed for a catalogue this size):
1. Gaps are the role's requirements the person does not meet yet: essentials first, then by weight.
2. For each gap, add the shortest verified course that still raises the skill, until it reaches
   the required level. A course adds at most one level if short and two if long, never beyond its
   own level (src/params.py). If no course can finish the job the gap is "partly covered"; if none
   exists it is listed as having no verified free course yet.
3. A course's prerequisites come before it; a course is taken once even if it closes several gaps.
4. Steps are laid out week by week at the person's weekly hours.
5. Every step names the skills it closes and the SDG targets those skills serve, with the reason.
The fit after the path is an estimate: it assumes the person finishes the steps and reaches the
level the course material covers.
"""

import math
from collections.abc import Mapping
from dataclasses import dataclass, field

from src import params
from src.match.engine import Evidence, RoleMatch, Scenario, score_role
from src.pack import Course, Pack, SdgLink

MINUTES_PER_HOUR = 60


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


@dataclass
class Pathway:
    role_id: str
    role_title: str
    weekly_hours: float
    steps: list[Step]
    total_hours: float
    weeks: int
    uncovered: list[str]  # skill names with no verified free course yet
    partly_covered: list[str]  # skill names a course raises but not to the required level
    essentials_unmet: list[str]  # essential skills still below level after the path
    fit_before: float
    fit_after: float
    sdg_summary: dict[str, list[str]]  # target -> mechanisms
    pathway_sdgs: list[SdgLink]


def _reach(course: Course) -> int:
    return params.COURSE_LEVEL_REACH[course.level]


def _max_gain(course: Course) -> int:
    if course.minutes < params.COURSE_SHORT_MINUTES:
        return params.COURSE_MAX_GAIN_SHORT
    return params.COURSE_MAX_GAIN_LONG


def _level_after(course: Course, current: int, required: int) -> int:
    """Level a skill reaches after this course: limited by course length, level and the need."""
    return max(current, min(_reach(course), current + _max_gain(course), required))


def _with_prerequisites(pack: Pack, course: Course, chosen: list[Course]) -> list[Course]:
    """The course preceded by any prerequisites not chosen yet (depth first)."""
    out: list[Course] = []
    for prereq_id in course.requires:
        prereq = pack.courses[prereq_id]
        if prereq not in chosen and prereq not in out:
            out += _with_prerequisites(pack, prereq, chosen + out)
    return [*out, course]


def _step_sdgs(pack: Pack, gains: list[SkillGain]) -> list[StepSdg]:
    seen: dict[str, StepSdg] = {}
    for gain in gains:
        for link in pack.sdg.skill_kinds[pack.skills[gain.skill].kind]:
            if link.target not in seen:
                target = pack.sdg.targets[link.target]
                seen[link.target] = StepSdg(link.target, target.title, link.how)
    return list(seen.values())


def plan_pathway(
    pack: Pack,
    match: RoleMatch,
    levels: Mapping[str, int | None],
    weekly_hours: float,
    scenario: Scenario,
    evidence: Evidence,
) -> Pathway:
    if weekly_hours <= 0:
        raise ValueError("weekly hours must be positive")
    gaps = [r for r in match.requirements if (r.claimed or 0) < r.required]
    gaps.sort(key=lambda r: (not r.essential, -r.weight))
    needed = {r.skill: r.required for r in match.requirements}
    current = {k: (v or 0) for k, v in levels.items()}
    chosen: list[Course] = []
    gains_by_course: dict[str, list[SkillGain]] = {}

    def take(course: Course) -> None:
        gains = []
        for skill in course.covers:
            if skill not in needed:
                continue
            before = current.get(skill, 0)
            after = _level_after(course, before, needed[skill])
            if after > before:
                gains.append(SkillGain(skill, pack.skills[skill].name, before, after))
                current[skill] = after
        chosen.append(course)
        gains_by_course[course.id] = gains

    uncovered: list[str] = []
    partly: list[str] = []
    for gap in gaps:
        if not pack.courses_for(gap.skill):
            uncovered.append(gap.skill_name)
            continue
        while current.get(gap.skill, 0) < gap.required:
            options = [
                c
                for c in pack.courses_for(gap.skill)
                if c not in chosen
                and _level_after(c, current.get(gap.skill, 0), gap.required)
                > current.get(gap.skill, 0)
            ]
            if not options:
                partly.append(gap.skill_name)
                break
            course = min(options, key=lambda c: c.minutes)
            for item in _with_prerequisites(pack, course, chosen):
                if item not in chosen:
                    take(item)

    steps: list[Step] = []
    elapsed = 0.0
    for order, course in enumerate(chosen, start=1):
        gains = gains_by_course[course.id]
        hours = round(course.minutes / MINUTES_PER_HOUR, 1)
        week_start = math.floor(elapsed / weekly_hours) + 1
        elapsed += hours
        week_end = max(week_start, math.ceil(elapsed / weekly_hours))
        steps.append(
            Step(
                order,
                course,
                hours,
                week_start,
                week_end,
                gains,
                _step_sdgs(pack, gains),
                [c.id for c in chosen if course.id in c.requires],
            )
        )

    after = score_role(pack, pack.destination_roles[match.role_id], current, scenario, evidence)
    summary: dict[str, list[str]] = {}
    for step in steps:
        for sdg in step.sdgs:
            summary.setdefault(sdg.target, [])
            if sdg.how not in summary[sdg.target]:
                summary[sdg.target].append(sdg.how)
    for link in [*pack.sdg.pathway, *pack.sdg.destination]:
        summary.setdefault(link.target, []).append(link.how)
    return Pathway(
        role_id=match.role_id,
        role_title=match.title,
        weekly_hours=weekly_hours,
        steps=steps,
        total_hours=round(sum(s.hours for s in steps), 1),
        weeks=steps[-1].week_end if steps else 0,
        uncovered=uncovered,
        partly_covered=partly,
        essentials_unmet=after.essential_gaps,
        fit_before=match.fit,
        fit_after=after.fit,
        sdg_summary=summary,
        pathway_sdgs=[*pack.sdg.pathway, *pack.sdg.destination],
    )
