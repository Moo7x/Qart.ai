"""Why a skill is on a role (and so on its plan): the evidence behind each requirement.

A requirement is evidenced in one of three ways, or it is our assumption, and the screen says which:
1. TalentCorp's GBS study names the skill for this role (the requirement's `pages`);
2. O*NET lists tasks of the role's occupation that use the skill (data/packs/gbs_fa/tasks.yaml);
3. O*NET lists software for the occupation that the skill is about (Technology Skills, mapped to
   skills in data/packs/gbs_fa/technology.yaml), flagged when job postings ask for it;
4. otherwise it is our assumption: TalentCorp lists the skill for GBS finance roles in general
   (the skill's own page), and we chose it for this role from the role's title and cluster.
Nothing here changes a score; it explains why the skill is counted at all.
"""

from functools import cache
from typing import Any, Literal

import yaml

from src.evidence.field import PACK_DIR, field_profile
from src.pack import Pack

TASKS_QUOTED = 1  # one task statement is enough to show the link; the rest stay one click away
TIER_TEXT = {"core": "main work of the role", "upskill": "skill to build", "support": "useful tool"}
Kind = Literal["talentcorp", "onet", "onet_tech", "assumption"]
TECH_SERIES = "onet_technology"  # src/collectors/onet.py
DEMAND_TEXT = {2.0: "in demand in job postings", 1.0: "often named in job postings", 0.0: "listed"}


@cache
def technology_map() -> dict[str, list[str]]:
    """O*NET software commodity title → the pack skills it is about (declared, with reasons)."""
    path = PACK_DIR / "technology.yaml"
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {entry["commodity"]: list(entry["skills"]) for entry in data.get("commodities", [])}


def _technology(soc: str, skill_id: str, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    """The strongest O*NET Technology Skills row for this occupation that is about the skill."""
    mapping = technology_map()
    best: dict[str, Any] | None = None
    for row in rows:
        if row.get("series") != TECH_SERIES or not str(row.get("entity", "")).startswith(soc + " "):
            continue
        span = str(row.get("cited_span", ""))
        title, _, examples = span.split(" · ", 2)[-1].partition(": ")
        if skill_id in mapping.get(title, []) and (best is None or row["value"] > best["value"]):
            best = {
                "value": row["value"],
                "title": title,
                "examples": examples,
                "period": row["period"],
            }
    return best


def requirement_basis(
    pack: Pack, role_id: str, skill_id: str, rows: list[dict[str, Any]] | None = None
) -> dict[str, Any]:
    role = pack.destination_roles[role_id]
    req = next(r for r in role.requires if r.skill == skill_id)
    skill = pack.skills[skill_id]
    tier = TIER_TEXT.get(req.tier, req.tier)
    if req.pages:
        return {
            "kind": "talentcorp",
            "text": f"TalentCorp names {skill.name} for {role.title} ({tier}).",
            "source": f"TalentCorp (2024) GBS study, PDF p. {', '.join(map(str, req.pages))}",
        }
    tasks = pack.tasks_for(role.soc, skill_id)
    if tasks:
        occupation = field_profile().occupation(role.soc)
        name = occupation.name if occupation else role.soc
        quoted = "; ".join(f"“{t.text}”" for t in tasks[:TASKS_QUOTED])
        return {
            "kind": "onet",
            "text": f"The job's own tasks use it ({tier}): {quoted}",
            "source": f"O*NET 31.0, {name} ({role.soc}), {len(tasks)} linked task(s)",
        }
    tech = _technology(role.soc, skill_id, rows or [])
    if tech:
        occupation = field_profile().occupation(role.soc)
        name = occupation.name if occupation else role.soc
        return {
            "kind": "onet_tech",
            "text": (
                f"Employers of {name} ask for {tech['title'].lower()} such as "
                f"{tech['examples'].split('; ')[0]} ({DEMAND_TEXT.get(tech['value'], 'listed')})."
            ),
            "source": f"O*NET {tech['period']} Technology Skills, {name} ({role.soc})",
        }
    return {
        "kind": "assumption",
        "text": (
            f"Our assumption ({tier}): TalentCorp lists {skill.name} for GBS finance roles in "
            f"general, not for {role.title} by name."
        ),
        "source": f"TalentCorp (2024) GBS study, PDF p. {skill.page}",
    }


def basis_kind(pack: Pack, role_id: str, skill_id: str) -> Kind:
    kind: Kind = requirement_basis(pack, role_id, skill_id)["kind"]
    return kind
