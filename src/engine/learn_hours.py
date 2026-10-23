"""Keep each skill's learn_hours in line with the real courses (pathway.md §3.4).

For each skill, `derived_hours` takes the verified courses that cover a level step and returns the
median of the hours they spend on that skill (the course hours divided by the skills it covers):
  to_basic      steps from "none" (0) up to "use sometimes" (0.7)
  to_confident  steps from "use sometimes" (0.7) up to "confident" (1.0)
A course that goes 0 → 1.0 counts for both, split in proportion to the two estimates. Only skills
with learn_hours_source "derived" are overwritten; hand-set "estimate" values never are.
"""

from collections.abc import Iterable, Mapping
from statistics import median

from src.contract import Course
from src.engine.catalogue import SkillInfo

BASIC = 0.7
CONFIDENT = 1.0


def step_samples(skill: SkillInfo, courses: Iterable[Course]) -> tuple[list[float], list[float]]:
    """Hours per course for this skill's two level steps (verified courses only)."""
    basic: list[float] = []
    confident: list[float] = []
    lh = skill.learn_hours
    for c in courses:
        if c.status != "verified":
            continue
        for step in c.skill_steps:
            if step.id != skill.id:
                continue
            share = c.hours / len(c.skill_steps)
            if step.from_level < BASIC and step.to_level >= CONFIDENT and lh:
                part = lh.to_basic / (lh.to_basic + lh.to_confident)
                basic.append(share * part)
                confident.append(share * (1 - part))
            elif step.from_level < BASIC <= step.to_level:
                basic.append(share)
            elif step.from_level >= BASIC and step.to_level >= CONFIDENT:
                confident.append(share)
    return basic, confident


def derived_hours(
    vocabulary: Mapping[str, SkillInfo], courses: Iterable[Course]
) -> dict[str, dict[str, float | None]]:
    """skill id -> {"to_basic": median or None, "to_confident": median or None}."""
    course_list = list(courses)
    out: dict[str, dict[str, float | None]] = {}
    for skill_id, skill in vocabulary.items():
        basic, confident = step_samples(skill, course_list)
        out[skill_id] = {
            "to_basic": round(median(basic), 1) if basic else None,
            "to_confident": round(median(confident), 1) if confident else None,
        }
    return out
