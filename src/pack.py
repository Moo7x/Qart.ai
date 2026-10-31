"""The field data pack (data/packs/gbs_fa): skills, roles and their requirements, read and checked.

Loading fails loudly if a role points to an unknown skill or role, so a typo in the YAML can never
silently drop a requirement.
"""

from functools import cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel

from src.evidence.field import PACK_DIR, field_profile

Tier = Literal["core", "upskill", "support"]

# Courses a released feedback correction marked unavailable (src/feedback/). Kept outside the
# cached pack so a correction applies at once; every planner reads courses through courses_for.
_UNAVAILABLE: set[str] = set()


def set_unavailable(course_ids: set[str]) -> None:
    _UNAVAILABLE.clear()
    _UNAVAILABLE.update(course_ids)


def unavailable() -> frozenset[str]:
    return frozenset(_UNAVAILABLE)


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
    pages: list[
        int
    ] = []  # TalentCorp (2024) PDF pages naming the role; the pack check requires one
    soc: str
    requires: list[Requirement]


class FitCheck(BaseModel):
    """How a candidate course's fit to its skills was checked (src/collectors/course_check.py)."""

    result: Literal["fits", "does_not_fit", "unclear"]
    by: str  # "person" or the model that read the page, e.g. "gpt-4.1-mini"
    quote: str = ""  # a sentence from the course's own page, found there by code
    checked: str = ""
    skills_removed: list[str] = []  # matched skills the page did not show it teaches


class Course(BaseModel):
    id: str
    title: str
    provider: str
    url: str
    minutes: int
    level: Literal["beginner", "intermediate", "advanced"]
    covers: list[str]
    requires: list[str] = []  # courses to take first (prerequisites)
    # What `minutes` measures: a provider's reading estimate (Microsoft Learn), guided study hours
    # stated by a programme, or a length the provider states without saying how it was counted.
    time_basis: Literal["reading_estimate", "guided_hours", "stated"] = "reading_estimate"
    hands_on: bool = False  # the material includes exercises the learner does, not only reading
    checked: str = ""  # date the entry was opened and checked, when it differs from its file's
    verified: bool = True  # False: a pipeline candidate not yet opened by a reviewer; never planned
    fit_check: FitCheck | None = None  # how a candidate became verified (none: checked by hand)


class SdgTarget(BaseModel):
    goal: int
    title: str
    text: str  # official UN wording


class SdgLink(BaseModel):
    target: str
    how: str  # the mechanism shown to the user
    source: str = ""  # where the link's basis is read (per-skill and per-role links, B7)


class SdgMap(BaseModel):
    source: str
    targets: dict[str, SdgTarget]
    skill_kinds: dict[str, list[SdgLink]]
    pathway: list[SdgLink]
    destination: list[SdgLink]
    # B7: each skill's and each destination role's own links; skill_kinds is the fallback.
    skills: dict[str, list[SdgLink]] = {}
    roles: dict[str, list[SdgLink]] = {}

    def for_skill(self, skill_id: str, kind: str) -> list[SdgLink]:
        return self.skills.get(skill_id) or self.skill_kinds[kind]

    def for_role(self, role_id: str) -> list[SdgLink]:
        return self.roles.get(role_id) or self.destination


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


class TechnologyCommodity(BaseModel):
    """A declared link from an exact O*NET software category to pack skills."""

    commodity: str
    skills: list[str]
    reason: str


class Pack(BaseModel):
    skills: dict[str, Skill]
    current_roles: dict[str, CurrentRole]
    destination_roles: dict[str, DestinationRole]
    courses: dict[str, Course]
    courses_checked: str
    sdg: SdgMap
    tasks: TaskCrosswalk
    technology: list[TechnologyCommodity] = []

    def courses_for(self, skill_id: str) -> list[Course]:
        return [
            c
            for c in self.courses.values()
            if skill_id in c.covers and c.verified and c.id not in _UNAVAILABLE
        ]

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
    commodities = [entry.commodity for entry in pack.technology]
    for entry in pack.technology:
        if not entry.commodity.strip() or commodities.count(entry.commodity) > 1:
            problems.append(f"technology: empty or duplicate commodity {entry.commodity!r}")
        if not entry.skills or not entry.reason.strip():
            problems.append(f"technology {entry.commodity}: needs skills and a reason")
        problems += [
            f"technology {entry.commodity}: unknown skill {skill}"
            for skill in entry.skills
            if skill not in pack.skills
        ]
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
        *(link for links in pack.sdg.skills.values() for link in links),
        *(link for links in pack.sdg.roles.values() for link in links),
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
    problems += _sdg_link_problems(pack)
    problems += _role_problems(pack)
    kinds = {s.kind for s in pack.skills.values()}
    problems += [
        f"skill kind {k} has no SDG mapping" for k in kinds if not pack.sdg.skill_kinds.get(k)
    ]
    if problems:
        raise PackError("; ".join(problems))


def _role_problems(pack: Pack) -> list[str]:
    """B10: a destination role is fully sourced: a study page, an essential and a known SOC code."""
    followed = {o.code for o in field_profile().soc_occupations}
    problems = []
    for role in pack.destination_roles.values():
        if not role.pages:
            problems.append(f"destination role {role.id} cites no study page")
        if not any(r.essential for r in role.requires):
            problems.append(f"destination role {role.id} has no essential requirement")
        if role.soc not in followed:
            problems.append(f"destination role {role.id}: SOC {role.soc} is not in field.yaml")
    return problems


def _sdg_link_problems(pack: Pack) -> list[str]:
    """B7: every skill and destination role has its own link, each with a reason and a source."""
    problems = [f"skill {s} has no SDG link" for s in pack.skills if not pack.sdg.skills.get(s)]
    problems += [
        f"destination role {r} has no SDG link"
        for r in pack.destination_roles
        if not pack.sdg.roles.get(r)
    ]
    problems += [
        f"SDG links name unknown skill {s}" for s in pack.sdg.skills if s not in pack.skills
    ]
    problems += [
        f"SDG links name unknown role {r}"
        for r in pack.sdg.roles
        if r not in pack.destination_roles
    ]
    for owner, links in [*pack.sdg.skills.items(), *pack.sdg.roles.items()]:
        problems += [
            f"SDG link {owner} → {link.target} needs a one-line reason and a source"
            for link in links
            if not link.how.strip() or "\n" in link.how.strip() or not link.source.strip()
        ]
    return problems


def pack_files(stem: str) -> list[Path]:
    """`<stem>.yaml` first, then any `<stem>_*.yaml` (e.g. a pipeline-built catalogue), by name."""
    return [PACK_DIR / f"{stem}.yaml", *sorted(PACK_DIR.glob(f"{stem}_*.yaml"))]


def _load_courses() -> tuple[dict[str, Course], str]:
    """Every course file merged; the hand-checked courses.yaml gives the catalogue's date."""
    courses: dict[str, Course] = {}
    checked = ""
    for path in pack_files("courses"):
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        checked = checked or str(raw["checked"])
        for item in raw["courses"]:
            course = Course.model_validate(item)
            if course.id in courses:
                raise PackError(f"{path.name}: course {course.id} is already defined")
            courses[course.id] = course
    return courses, checked


@cache
def load_pack() -> Pack:
    skills = yaml.safe_load((PACK_DIR / "skills.yaml").read_text(encoding="utf-8"))
    roles = yaml.safe_load((PACK_DIR / "roles.yaml").read_text(encoding="utf-8"))
    courses, courses_checked = _load_courses()
    sdg = yaml.safe_load((PACK_DIR / "sdg.yaml").read_text(encoding="utf-8"))
    technology_path = PACK_DIR / "technology.yaml"
    technology = (
        yaml.safe_load(technology_path.read_text(encoding="utf-8")) or {}
        if technology_path.exists()
        else {}
    )
    pack = Pack(
        skills={s["id"]: Skill.model_validate(s) for s in skills},
        current_roles={r["id"]: CurrentRole.model_validate(r) for r in roles["current_roles"]},
        destination_roles={
            r["id"]: DestinationRole.model_validate(r) for r in roles["destination_roles"]
        },
        courses=courses,
        courses_checked=courses_checked,
        sdg=SdgMap.model_validate(sdg),
        tasks=TaskCrosswalk.model_validate(
            yaml.safe_load((PACK_DIR / "tasks.yaml").read_text(encoding="utf-8"))
        ),
        technology=[
            TechnologyCommodity.model_validate(entry) for entry in technology.get("commodities", [])
        ],
    )
    _check(pack)
    return pack
