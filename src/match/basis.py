"""Why a skill is on a role (and so on its plan): the evidence behind each requirement.

A requirement is evidenced in one of two ways, or it is our assumption, and the screen says which:
1. TalentCorp's GBS study names the skill for this role (the requirement's `pages`);
2. O*NET lists tasks of the role's occupation that use the skill (data/packs/gbs_fa/tasks.yaml);
3. otherwise it is our assumption: TalentCorp lists the skill for GBS finance roles in general
   (the skill's own page), and we chose it for this role from the role's title and cluster.
Nothing here changes a score; it explains why the skill is counted at all.
"""

from typing import Any, Literal

from src.evidence.field import field_profile
from src.pack import Pack

TASKS_QUOTED = 1  # one task statement is enough to show the link; the rest stay one click away
TIER_TEXT = {"core": "main work of the role", "upskill": "skill to build", "support": "useful tool"}
Kind = Literal["talentcorp", "onet", "assumption"]


def requirement_basis(pack: Pack, role_id: str, skill_id: str) -> dict[str, Any]:
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
