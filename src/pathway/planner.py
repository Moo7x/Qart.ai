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
6. The plan adapts to the person (B5), and says so in `adjustments`: AI basics are skipped when
   the person shows AI or automation work with evidence (`ai_basics_choice`); a skill already at
   what study gives goes straight to practice, so no course (beginner or other) is planned for it.
Fits after the plan are estimates: after study assumes the person finishes the courses; after
practice also assumes the practice targets are reached. Both are ranges by the C2 rule, with
planned levels counted as unevidenced (src/match/decision.py fit_range).
"""

import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from typing import Any

from src import params
from src.journey.store import SkillClaim, levels_of
from src.match.decision import fit_range, is_evidenced
from src.match.engine import Evidence, RequirementScore, RoleMatch, Scenario, score_role
from src.pack import Course, Pack, SdgLink
from src.pathway.practice import load_practice

MINUTES_PER_HOUR = 60
AI_BASICS_REASON = "AI basics come first: adapting to AI starts with knowing how to use it safely."
AI_BASICS_ALWAYS_REASON = (
    "AI basics come first for students and career switchers, whatever the CV shows."
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


@dataclass(frozen=True)
class TimeEstimate:
    """A step's time (C3): hours for a course; a week range (estimate) for practice."""

    value: float
    unit: str  # "hours" or "weeks"
    basis: str
    low: float | None = None
    high: float | None = None


@dataclass(frozen=True)
class WeekRange:
    low: int
    high: int
    kind: str = "estimate"


@dataclass(frozen=True)
class FitRange:
    low: float
    high: float
    kind: str = "estimate"


@dataclass(frozen=True)
class Adjustment:
    rule: str  # "ai_basics_skipped" or "straight_to_practice"
    text: str


@dataclass(frozen=True)
class AiBasics:
    shown: bool
    reason: str


@dataclass
class Step:
    order: int
    course: Course
    hours: float
    week_start: int
    week_end: int
    gains: list[SkillGain]
    sdgs: list[StepSdg]
    prerequisite_for: list[str]  # course ids that need this one
    # C3 fields (docs/PHASE2_PLAN.md §4): the same shape as a practice step.
    id: str
    skill: str  # the gap this course was added for
    target_level: int
    time: TimeEstimate
    unlock: str | None
    kind: str = "course"
    locked: bool = False
    done: bool = False


@dataclass
class PracticeStep:
    order: int
    id: str  # "practice:<skill>:<level>"
    skill: str
    skill_name: str
    target_level: int
    text: str
    show_by: str
    time: TimeEstimate
    week_start: dict[str, int]  # after the skill's study steps, as a range
    basis: list[dict[str, str]]
    kind: str = "practice"
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
    total_hours: float  # the study hours (the API also names them `study_hours`, C3)
    weeks: int
    uncovered: list[str]  # skill names with no verified free course yet
    partly_covered: list[str]  # skill names study raises, but not to the level study can give
    essentials_unmet: list[str]  # essential skills still below level after the study steps
    fit_before: float
    fit_after: float  # after the study steps (estimate)
    sdg_summary: dict[str, list[str]]  # target -> mechanisms
    pathway_sdgs: list[SdgLink]
    practice_steps: list[PracticeStep]
    practice_weeks: WeekRange
    fit_after_study: FitRange
    fit_after_practice: FitRange
    free_share: float | None  # share of study hours in free courses; None = no study
    ai_basics: AiBasics
    study_levels: dict[str, int]  # gap skill -> level after study
    # B5: every way this plan was adjusted for the person, each with the rule behind it.
    adjustments: list[Adjustment]
    free_share_basis: str = FREE_SHARE_BASIS

    @property
    def gap_skills(self) -> set[str]:
        """The role's skills the person is below on today: the skills this plan is for."""
        return set(self.study_levels)


def pathway_out(path: Pathway) -> dict[str, Any]:
    """The plan as the API returns it, with the C3 field names unchanged."""
    return {**asdict(path), "study_hours": path.total_hours}


def ai_basics_choice(
    pack: Pack, claims: Mapping[str, SkillClaim], situation: str | None
) -> AiBasics:
    """Show AI basics unless an evidenced claim shows AI or automation work (B5)."""
    if situation in params.AI_BASICS_ALWAYS:
        return AiBasics(True, AI_BASICS_ALWAYS_REASON)
    for skill in params.AI_BASICS_SKILLS:
        claim = claims.get(skill)
        if (
            claim is not None
            and (claim.level or 0) >= params.AI_BASICS_SKIP_LEVEL
            and is_evidenced(claim)
        ):
            name = pack.skills[skill].name
            return AiBasics(False, f"Skipped: your CV shows ‘{claim.evidence}’ ({name}).")
    return AiBasics(True, AI_BASICS_REASON)


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
        for link in pack.sdg.for_skill(skill, pack.skills[skill].kind):
            if link.target not in seen:
                target = pack.sdg.targets[link.target]
                seen[link.target] = StepSdg(link.target, target.title, link.how)
    return list(seen.values())


def _planned_claims(
    claims: Mapping[str, SkillClaim], planned: Mapping[str, int | None]
) -> dict[str, SkillClaim]:
    """Today's claims, with each level the plan changes as an unevidenced claim."""
    out, today = dict(claims), levels_of(claims)
    for skill, level in planned.items():
        if level is not None and level != today.get(skill):
            out[skill] = SkillClaim(level=level, source="self")
    return out


@dataclass
class Study:
    """Rule 2's result: the courses chosen for the gaps, and what study leaves out."""

    gaps: list[RequirementScore]  # essentials first, then by weight
    needed: dict[str, int]  # skill -> the level the role needs
    start: dict[str, int]  # skill -> today's stated level (unstated as 0)
    chosen: list[Course] = field(default_factory=list)
    reason: dict[str, str] = field(default_factory=dict)  # course id -> the gap it was added for
    uncovered: list[str] = field(default_factory=list)
    partly: list[str] = field(default_factory=list)
    adjustments: list[Adjustment] = field(default_factory=list)

    def level(self, courses: list[Course], skill: str) -> int:
        return level_after_study(courses, skill, self.start.get(skill, 0), self.needed[skill])

    def levels_after(self) -> dict[str, int]:
        """Levels after the chosen courses. With no course planned, skills the person did not
        state stay unstated; with any course, every needed skill gets a level."""
        if not self.chosen:
            return dict(self.start)
        return {**self.start, **{s: self.level(self.chosen, s) for s in self.needed}}


def choose_courses(pack: Pack, match: RoleMatch, start: dict[str, int]) -> Study:
    """Rule 2: per gap, the shortest verified courses until study gives what it can; a skill
    already at STUDY_MAX_LEVEL goes straight to practice."""
    gaps = sorted(
        (r for r in match.requirements if (r.claimed or 0) < r.required),
        key=lambda r: (not r.essential, -r.weight),
    )
    study = Study(gaps, {r.skill: r.required for r in match.requirements}, start)
    for gap in gaps:
        if start.get(gap.skill, 0) >= params.STUDY_MAX_LEVEL:
            study.adjustments.append(
                Adjustment(
                    "straight_to_practice",
                    f"Straight to practice for {gap.skill_name}: you are at level "
                    f"{start[gap.skill]}, the most study can give.",
                )
            )
            continue  # no course can raise it, so none is planned and none is "missing"
        options = pack.courses_for(gap.skill)
        if not options:
            study.uncovered.append(gap.skill_name)
            continue
        # The most study can give with every course available; courses beyond it add nothing.
        unused = [c for c in options if c not in study.chosen]
        reachable = study.level(study.chosen + unused, gap.skill)
        for course in sorted(options, key=lambda c: (c.minutes, c.id)):
            if study.level(study.chosen, gap.skill) >= reachable:
                break
            if course in study.chosen:
                continue
            for item in _with_prerequisites(pack, course, study.chosen):
                if item not in study.chosen:
                    study.chosen.append(item)
                    study.reason.setdefault(item.id, gap.skill)
        if study.level(study.chosen, gap.skill) < min(gap.required, params.STUDY_MAX_LEVEL):
            study.partly.append(gap.skill_name)
    return study


def schedule(pack: Pack, study: Study, weekly_hours: float) -> tuple[list[Step], dict[str, int]]:
    """Rule 4: the chosen courses week by week with their gains and SDG links, and the week
    each needed skill's study ends (its practice starts after it)."""
    gap_skills = {g.skill for g in study.gaps}
    steps: list[Step] = []
    elapsed = 0.0
    taken: list[Course] = []
    study_end: dict[str, int] = {}
    for order, course in enumerate(study.chosen, start=1):
        covered = [s for s in course.covers if s in study.needed]
        before = {s: study.level(taken, s) for s in covered}
        taken.append(course)
        gains = [
            SkillGain(s, pack.skills[s].name, b, reached)
            for s, b in before.items()
            if (reached := study.level(taken, s)) > b
        ]
        hours = round(course.minutes / MINUTES_PER_HOUR, 1)
        week_start = math.floor(elapsed / weekly_hours) + 1
        elapsed += hours
        week_end = max(week_start, math.ceil(elapsed / weekly_hours))
        study_end.update({s: week_end for s in covered})
        skill = study.reason.get(course.id, gains[0].skill if gains else "")
        steps.append(
            Step(
                order=order,
                course=course,
                hours=hours,
                week_start=week_start,
                week_end=week_end,
                gains=gains,
                sdgs=_step_sdgs(pack, [s for s in course.covers if s in gap_skills]),
                prerequisite_for=[c.id for c in study.chosen if course.id in c.requires],
                id=course.id,
                skill=skill,
                target_level=study.level(taken, skill) if skill in study.needed else 0,
                time=TimeEstimate(hours, "hours", course.time_basis),
                unlock="previous_step" if order > 1 else None,
            )
        )
    return steps, study_end


def _sdg_summary(pack: Pack, role_id: str, steps: list[Step]) -> dict[str, list[str]]:
    """Target -> the mechanisms the plan's steps and the path itself serve it by."""
    summary: dict[str, list[str]] = {}
    for step in steps:
        for sdg in step.sdgs:
            summary.setdefault(sdg.target, [])
            if sdg.how not in summary[sdg.target]:
                summary[sdg.target].append(sdg.how)
    for link in [*pack.sdg.pathway, *pack.sdg.for_role(role_id)]:
        summary.setdefault(link.target, []).append(link.how)
    return summary


def plan_pathway(
    pack: Pack,
    match: RoleMatch,
    claims: Mapping[str, SkillClaim],
    weekly_hours: float,
    scenario: Scenario,
    evidence: Evidence,
    situation: str | None = None,
) -> Pathway:
    """The person's plan to `match`'s role. `claims` are the person's claims (for synthetic
    level maps, src/journey/store.py `claims_from_levels`)."""
    if weekly_hours <= 0:
        raise ValueError("weekly hours must be positive")
    levels = levels_of(claims)
    study = choose_courses(pack, match, {k: (v or 0) for k, v in levels.items()})
    steps, study_end = schedule(pack, study, weekly_hours)
    reached = study.levels_after()
    practice = _practice_steps(study.gaps, reached, study_end, len(steps))
    basics = ai_basics_choice(pack, claims, situation)
    skipped = [] if basics.shown else [Adjustment("ai_basics_skipped", basics.reason)]

    role = pack.destination_roles[match.role_id]
    after_study: dict[str, int | None] = {**levels, **reached}
    after_practice = {**after_study, **{p.skill: p.target_level for p in practice}}
    studied = score_role(pack, role, after_study, scenario, evidence)
    practised = score_role(pack, role, after_practice, scenario, evidence)
    total = round(sum(s.hours for s in steps), 1)
    return Pathway(
        role_id=match.role_id,
        role_title=match.title,
        weekly_hours=weekly_hours,
        steps=steps,
        total_hours=total,
        weeks=steps[-1].week_end if steps else 0,
        uncovered=study.uncovered,
        partly_covered=study.partly,
        essentials_unmet=studied.essential_gaps,
        fit_before=match.fit,
        fit_after=studied.fit,
        sdg_summary=_sdg_summary(pack, match.role_id, steps),
        pathway_sdgs=[*pack.sdg.pathway, *pack.sdg.for_role(match.role_id)],
        practice_steps=practice,
        practice_weeks=WeekRange(
            sum(int(p.time.low or 0) for p in practice),
            sum(int(p.time.high or 0) for p in practice),
        ),
        fit_after_study=_range(
            pack, studied, _planned_claims(claims, after_study), scenario, evidence
        ),
        fit_after_practice=_range(
            pack, practised, _planned_claims(claims, after_practice), scenario, evidence
        ),
        free_share=1.0 if total else None,
        ai_basics=basics,
        study_levels={g.skill: reached.get(g.skill, 0) for g in study.gaps},
        adjustments=[*skipped, *study.adjustments],
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
    claims: Mapping[str, SkillClaim],
    scenario: Scenario,
    evidence: Evidence,
) -> FitRange:
    found = fit_range(pack, match, claims, scenario, evidence)
    return FitRange(found["low"], found["high"])


def _practice_steps(
    gaps: list[RequirementScore],
    after_study: Mapping[str, int],
    study_end: Mapping[str, int],
    first_order: int,
) -> list[PracticeStep]:
    """Rule 3: one practice step per level above STUDY_MAX_LEVEL, after the skill's study."""
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
                    id=practice_step_id(gap.skill, level),
                    skill=gap.skill,
                    skill_name=gap.skill_name,
                    target_level=level,
                    text=task.text,
                    show_by=task.show_by,
                    time=TimeEstimate(
                        task.weeks_low,
                        "weeks",
                        "practice_estimate",
                        task.weeks_low,
                        task.weeks_high,
                    ),
                    week_start={"low": low + 1, "high": high + 1},
                    basis=[b.model_dump() for b in task.basis],
                )
            )
            low += task.weeks_low
            high += task.weeks_high
    return out
