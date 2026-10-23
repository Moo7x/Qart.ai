"""The field data pack (data/packs/gbs_fa): skills, roles and their requirements, read and checked.

Loading fails loudly if a role points to an unknown skill or role, so a typo in the YAML can never
silently drop a requirement.
"""

from functools import cache
from typing import Literal

import yaml
from pydantic import BaseModel

from src.evidence.field import PACK_DIR

Tier = Literal["core", "upskill", "support"]
AiRole = Literal["routine", "complement", "neutral"]


class Skill(BaseModel):
    id: str
    name: str
    kind: Literal["finance_core", "data_digital", "green", "business"]
    ai_role: AiRole
    page: int  # TalentCorp PDF page that names the skill


class Requirement(BaseModel):
    skill: str
    tier: Tier
    essential: bool = False
    pages: list[int] = []  # TalentCorp pages linking this skill to this role (upskill tier)


class CurrentRole(BaseModel):
    id: str
    title: str
    impact: Literal["high", "medium", "low"]
    page: int
    soc: str
    summary: str
    typical_skills: list[str]
    transitions: list[str]
    other_sectors: list[str]


class DestinationRole(BaseModel):
    id: str
    title: str
    impact: Literal["high", "medium", "low"]
    soc: str
    requires: list[Requirement]


class Course(BaseModel):
    id: str
    title: str
    provider: str
    url: str
    minutes: int
    level: Literal["beginner", "intermediate", "advanced"]
    covers: list[str]
    requires: list[str] = []  # courses to take first (prerequisites)


class SdgTarget(BaseModel):
    goal: int
    title: str
    text: str  # official UN wording


class SdgLink(BaseModel):
    target: str
    how: str  # the mechanism shown to the user


class SdgMap(BaseModel):
    source: str
    targets: dict[str, SdgTarget]
    skill_kinds: dict[str, list[SdgLink]]
    pathway: list[SdgLink]
    destination: list[SdgLink]


class TaskLink(BaseModel):
    task: int  # O*NET task id (also the Economic Index node id for that task)
    text: str  # verbatim O*NET task statement


class TaskOccupation(BaseModel):
    title: str
    skills: dict[str, list[TaskLink]]  # pack skill id -> the O*NET tasks that show it


class TaskCrosswalk(BaseModel):
    """data/packs/gbs_fa/tasks.yaml: declared links from role skills to O*NET tasks."""

    source: str
    source_url: str
    licence: str
    occupations: dict[str, TaskOccupation]  # O*NET-SOC code -> links


class Pack(BaseModel):
    skills: dict[str, Skill]
    current_roles: dict[str, CurrentRole]
    destination_roles: dict[str, DestinationRole]
    courses: dict[str, Course]
    courses_checked: str
    sdg: SdgMap
    tasks: TaskCrosswalk

    def courses_for(self, skill_id: str) -> list[Course]:
        return [c for c in self.courses.values() if skill_id in c.covers]

    def tasks_for(self, soc: str, skill_id: str) -> list[TaskLink]:
        occupation = self.tasks.occupations.get(soc)
        return occupation.skills.get(skill_id, []) if occupation else []

    def task_ids(self) -> set[str]:
        """Every linked O*NET task id, as the collectors filter source rows by it."""
        return {
            str(link.task)
            for occupation in self.tasks.occupations.values()
            for links in occupation.skills.values()
            for link in links
        }


class PackError(ValueError):
    """The pack files contradict each other."""


def _check(pack: Pack) -> None:
    problems = []
    for role in pack.current_roles.values():
        problems += [
            f"{role.id}: unknown skill {s}" for s in role.typical_skills if s not in pack.skills
        ]
        problems += [
            f"{role.id}: unknown destination {d}"
            for d in role.transitions
            if d not in pack.destination_roles
        ]
    for dest in pack.destination_roles.values():
        seen = [r.skill for r in dest.requires]
        problems += [f"{dest.id}: unknown skill {s}" for s in seen if s not in pack.skills]
        problems += [f"{dest.id}: {s} listed twice" for s in set(seen) if seen.count(s) > 1]
        problems += [
            f"{dest.id}: upskill {r.skill} has no page"
            for r in dest.requires
            if r.tier == "upskill" and not r.pages
        ]
        if not any(r.essential for r in dest.requires):
            problems.append(f"{dest.id}: no essential requirement")
    for course in pack.courses.values():
        problems += [
            f"{course.id}: unknown skill {s}" for s in course.covers if s not in pack.skills
        ]
        problems += [
            f"{course.id}: unknown prerequisite {c}"
            for c in course.requires
            if c not in pack.courses
        ]
        if not course.url.startswith("https://"):
            problems.append(f"{course.id}: url is not https")
    links = [
        *pack.sdg.pathway,
        *pack.sdg.destination,
        *(link for kind in pack.sdg.skill_kinds.values() for link in kind),
    ]
    problems += [
        f"SDG link to unknown target {link.target}"
        for link in links
        if link.target not in pack.sdg.targets
    ]
    for soc, occupation in pack.tasks.occupations.items():
        roles = [d for d in pack.destination_roles.values() if d.soc == soc]
        if not roles:
            problems.append(f"tasks: no destination role in occupation {soc}")
        needed = {r.skill for d in roles for r in d.requires}
        problems += [
            f"tasks {soc}: {s} is not required by a role in this occupation"
            for s in occupation.skills
            if s not in needed
        ]
    kinds = {s.kind for s in pack.skills.values()}
    problems += [
        f"skill kind {k} has no SDG mapping" for k in kinds if not pack.sdg.skill_kinds.get(k)
    ]
    if problems:
        raise PackError("; ".join(problems))


@cache
def load_pack() -> Pack:
    skills = yaml.safe_load((PACK_DIR / "skills.yaml").read_text(encoding="utf-8"))
    roles = yaml.safe_load((PACK_DIR / "roles.yaml").read_text(encoding="utf-8"))
    courses = yaml.safe_load((PACK_DIR / "courses.yaml").read_text(encoding="utf-8"))
    sdg = yaml.safe_load((PACK_DIR / "sdg.yaml").read_text(encoding="utf-8"))
    pack = Pack(
        skills={s["id"]: Skill.model_validate(s) for s in skills},
        current_roles={r["id"]: CurrentRole.model_validate(r) for r in roles["current_roles"]},
        destination_roles={
            r["id"]: DestinationRole.model_validate(r) for r in roles["destination_roles"]
        },
        courses={c["id"]: Course.model_validate(c) for c in courses["courses"]},
        courses_checked=str(courses["checked"]),
        sdg=SdgMap.model_validate(sdg),
        tasks=TaskCrosswalk.model_validate(
            yaml.safe_load((PACK_DIR / "tasks.yaml").read_text(encoding="utf-8"))
        ),
    )
    _check(pack)
    return pack
