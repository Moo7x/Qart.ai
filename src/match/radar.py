"""Personal Future Skills Radar: the skills of one role for this person, and the field signals that
concern their current occupation (PLAN §2 screen 2).

Axes are the requirements of the person's chosen destination (or their best-fitting role when none
is chosen yet). Each axis carries three separately labelled facts:
  * levels   – the person's claim, the level the role needs, and the level after the planned
               pathway (an estimate from the declared course rules);
  * emphasis – whether the scenario raises or lowers the skill's weight (an assumption), with the
               observed AI use behind it (task- or occupation-level);
  * demand   – whether TalentCorp names the skill as in demand (expert view).
The field signals are the existing signals filtered to the person's current occupation: its DOSM
major group, its DOSM job-ad series and its Economic Index AI use. Pure: no I/O here.
"""

import re
from typing import Any

from src.evidence.field import field_profile
from src.evidence.signals import Signal
from src.match.engine import RoleMatch
from src.match.outlook import MAJOR_GROUP
from src.pack import Pack
from src.pathway.planner import Pathway

Row = dict[str, Any]
# A weight factor this close to 1 is no shift (floating-point tolerance, not a policy value).
SHIFT_EPSILON = 1e-9


def _squash(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def _emphasis(weight: float, base: float, essential: bool) -> str:
    if essential:
        return "fixed"  # essentials keep their weight in every scenario
    if weight > base + SHIFT_EPSILON:
        return "rising"
    if weight < base - SHIFT_EPSILON:
        return "weakening"
    return "stable"


def radar(
    pack: Pack,
    match: RoleMatch,
    path: Pathway,
    chosen: bool,
    rows: list[Row],
    signals: list[Signal],
    current_role: str | None,
) -> dict[str, Any]:
    in_demand = {
        _squash(r["entity"])
        for r in rows
        if r["source_id"] == "talentcorp_gbs_2024" and r["series"] == "talentcorp_in_demand_skill"
    }
    after = {g.skill: g.after for step in path.steps for g in step.gains}
    axes = []
    for req in match.requirements:
        skill = pack.skills[req.skill]
        observed = [t for t in req.tasks if t.automation_share is not None]
        axes.append(
            {
                "skill": req.skill,
                "name": skill.name,
                "kind": skill.kind,
                "essential": req.essential,
                "claimed": req.claimed,
                "required": req.required,
                "after": max(after.get(req.skill, 0), req.claimed or 0),
                "emphasis": _emphasis(req.weight, req.base_weight, req.essential),
                "weight_factor": req.weight / req.base_weight,
                "reason": req.shift_reason,
                "ai_use": (
                    {
                        "automation_share": req.automation_share,
                        "basis": req.automation_basis,
                        "tasks_observed": len(observed),
                        "tasks_linked": len(req.tasks),
                    }
                    if req.automation_share is not None
                    else None
                ),
                "in_demand": _squash(skill.name) in in_demand if in_demand else None,
            }
        )
    return {
        "role_id": match.role_id,
        "title": match.title,
        "chosen": chosen,
        "fit": match.fit,
        "fit_after": path.fit_after,
        "axes": axes,
        "field_signals": [s.model_dump() for s in _personal_signals(pack, current_role, signals)],
    }


def _personal_signals(pack: Pack, current_role: str | None, signals: list[Signal]) -> list[Signal]:
    role = pack.current_roles.get(current_role or "")
    if role is None:
        return []
    occupation = field_profile().occupation(role.soc)
    wanted: list[str] = []
    if occupation and occupation.isco and occupation.isco[0] in MAJOR_GROUP:
        wanted.append(f"dosm_share_{MAJOR_GROUP[occupation.isco[0]]}")
    if occupation:
        wanted.append(f"dosm_jmi_{occupation.name.lower().replace(' ', '_')}")
    # The AI-use signal of an occupation exists for one geography only (Malaysia when it has two
    # months, otherwise global), so at most one of these two ids is present.
    wanted += [f"aei_{role.soc}_{field_profile().country}", f"aei_{role.soc}_GLOBAL"]
    by_id = {s.id: s for s in signals}
    return [by_id[i] for i in wanted if i in by_id]
