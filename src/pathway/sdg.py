"""SDG contribution of a person's plan (docs/PHASE2_PLAN.md §4 C4): skills × targets in hours.

Rules (B7):
* A study step's hours are split equally over the gap skills its material serves, the same
  "serves" rule the planner uses for a step's SDG links.
* A skill's hours count toward every target that skill serves, so the per-target totals are not
  added across targets (the response says so).
* Practice steps are a marker on their skill's row, never hours.
* Path-level links: free learning (4.3) and the destination role's own links (8.5 …).
Pure: also used by owner A's status page for platform totals.
"""

from collections import defaultdict

from pydantic import BaseModel

from src.pack import Pack
from src.pathway.planner import Pathway

NOTE = "Hours count toward every target a skill serves, so totals are not added across targets."


class SdgTargetOut(BaseModel):
    id: str
    title: str
    text: str  # official UN wording


class SdgRow(BaseModel):
    skill: str
    skill_name: str
    steps: list[str]  # course ids of the study steps that serve this skill
    practice: bool  # the skill also has a practice step (a marker, not hours)


class SdgReason(BaseModel):
    text: str
    source: str


class SdgCell(BaseModel):
    skill: str
    target: str
    hours: float
    reasons: list[SdgReason]


class SdgPathLink(BaseModel):
    target: str
    text: str
    source: str


class SdgTotal(BaseModel):
    target: str
    hours: float


class SdgRoleTarget(BaseModel):
    target: str
    reason: str
    source: str


class SdgRole(BaseModel):
    role_id: str
    title: str
    targets: list[SdgRoleTarget]


class SdgMatrix(BaseModel):
    targets: list[SdgTargetOut]
    rows: list[SdgRow]
    cells: list[SdgCell]
    path_links: list[SdgPathLink]
    totals: list[SdgTotal]
    roles: list[SdgRole]
    note: str
    source: str


def sdg_matrix(pack: Pack, pathway: Pathway) -> SdgMatrix:
    role = pack.destination_roles[pathway.role_id]
    gap_skills = [r.skill for r in role.requires if r.skill in pathway.study_levels]
    practised = {p.skill for p in pathway.practice_steps}
    hours: dict[str, float] = defaultdict(float)
    steps: dict[str, list[str]] = defaultdict(list)
    for step in pathway.steps:
        served = [s for s in step.course.covers if s in gap_skills]
        for skill in served:
            hours[skill] += step.hours / len(served)
            steps[skill].append(step.course.id)
    rows = [
        SdgRow(
            skill=s,
            skill_name=pack.skills[s].name,
            steps=steps.get(s, []),
            practice=s in practised,
        )
        for s in gap_skills
    ]
    cells = []
    for s in gap_skills:
        by_target: dict[str, list[SdgReason]] = defaultdict(list)
        for link in pack.sdg.for_skill(s, pack.skills[s].kind):
            by_target[link.target].append(SdgReason(text=link.how, source=link.source))
        cells += [
            SdgCell(skill=s, target=t, hours=round(hours.get(s, 0.0), 2), reasons=reasons)
            for t, reasons in by_target.items()
        ]
    path_links = [
        SdgPathLink(target=link.target, text=link.how, source=link.source or pack.sdg.source)
        for link in [*pack.sdg.pathway, *pack.sdg.for_role(role.id)]
    ]
    used = sorted(
        {c.target for c in cells} | {link.target for link in path_links},
        key=lambda t: [int(x) for x in t.split(".")],
    )
    totals = [
        SdgTotal(target=t, hours=round(sum(c.hours for c in cells if c.target == t), 2))
        for t in used
    ]
    roles = [
        SdgRole(
            role_id=r.id,
            title=r.title,
            targets=[
                SdgRoleTarget(target=link.target, reason=link.how, source=link.source)
                for link in pack.sdg.for_role(r.id)
            ],
        )
        for r in pack.destination_roles.values()
    ]
    targets = [
        SdgTargetOut(id=t, title=pack.sdg.targets[t].title, text=pack.sdg.targets[t].text)
        for t in used
    ]
    return SdgMatrix(
        targets=targets,
        rows=rows,
        cells=cells,
        path_links=path_links,
        totals=totals,
        roles=roles,
        note=NOTE,
        source=pack.sdg.source,
    )
