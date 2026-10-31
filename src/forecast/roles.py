"""The roles the industry forecast covers (data/packs/gbs_fa/industry_roles.yaml)."""

from functools import cache

import yaml
from pydantic import BaseModel

from src.evidence.field import PACK_DIR, field_profile
from src.pack import load_pack


class IndustryRole(BaseModel):
    id: str
    title: str
    talentcorp: str | None = None  # the name in the `talentcorp_role_impact` series
    pack_role: str | None = None  # a current or destination role of roles.yaml
    soc: str | None = None  # the O*NET occupation it is measured through
    soc_reason: str | None = None  # why this SOC, when it is our mapping


class IndustryRoles(BaseModel):
    version: str
    source: str
    roles: list[IndustryRole]


@cache
def industry_roles() -> IndustryRoles:
    raw = yaml.safe_load((PACK_DIR / "industry_roles.yaml").read_text(encoding="utf-8"))
    return IndustryRoles.model_validate(raw)


def check() -> list[str]:
    """Problems with the file: unknown pack roles, SOCs outside the field, SOCs that disagree."""
    pack = load_pack()
    known: dict[str, str] = {k: r.soc for k, r in pack.destination_roles.items()}
    known |= {k: r.soc for k, r in pack.current_roles.items()}
    followed = field_profile().soc_codes()
    problems = []
    for role in industry_roles().roles:
        if role.pack_role is not None and role.pack_role not in known:
            problems.append(f"{role.id}: unknown pack role {role.pack_role}")
        elif role.pack_role is not None and known[role.pack_role] != role.soc:
            problems.append(f"{role.id}: SOC differs from roles.yaml")
        if role.soc is not None and role.soc not in followed:
            problems.append(f"{role.id}: SOC {role.soc} is not followed in field.yaml")
        if role.pack_role is None and not role.soc_reason:
            problems.append(f"{role.id}: our own mapping needs a soc_reason")
    return problems
