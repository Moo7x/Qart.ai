"""Role catalogue and families for the role ranking (QART_NEXT_STEPS §5.1).

catalogue/target_roles.json: ~15 roles, each based on a public O*NET occupation (or code TODO
when none fits), with 5–8 skills weighted 3 (core) or 1 (nice to have).
catalogue/families.json: role families and their (symmetric) adjacency, for direction fit.
Separate from catalogue/roles.json, which the practice-evidence engine and HR views use.
"""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.engine.catalogue import CATALOGUE_DIR

CORE_WEIGHT = 3  # DECLARED: core skill
NICE_WEIGHT = 1  # DECLARED: nice to have
EducationLevel = Literal["secondary", "certification", "diploma", "bachelor", "master"]


class RoleSource(BaseModel):
    dataset: str
    code: str  # an O*NET-SOC code checked on O*NET OnLine, or "TODO"
    title: str | None
    url: str | None
    verified: bool
    retrieved: str | None = None
    note: str | None = None
    candidates: list[str] = []


class RoleSkill(BaseModel):
    id: str
    weight: Literal[1, 3]
    required_level: float | None = None  # overrides the role default


class RequiredLevel(BaseModel):
    default: float = Field(gt=0, le=1)


class TargetRole(BaseModel):
    id: str
    name: str
    family: str
    source: RoleSource
    typical_industries: list[str]
    min_education: EducationLevel
    skills: list[RoleSkill]
    required_level: RequiredLevel

    def required(self, skill: RoleSkill) -> float:
        return (
            skill.required_level
            if skill.required_level is not None
            else self.required_level.default
        )

    @property
    def core_skills(self) -> list[RoleSkill]:
        return [s for s in self.skills if s.weight == CORE_WEIGHT]


class Family(BaseModel):
    id: str
    name: str
    adjacent: list[str]


class RoleCatalogue(BaseModel):
    roles: list[TargetRole]
    families: list[Family]

    @property
    def family_ids(self) -> set[str]:
        return {f.id for f in self.families}

    def adjacent(self, a: str, b: str) -> bool:
        return any(f.id == a and b in f.adjacent for f in self.families)


def load_role_catalogue(directory: Path = CATALOGUE_DIR) -> RoleCatalogue:
    def read(name: str) -> Any:
        return json.loads((directory / name).read_text(encoding="utf-8"))

    return RoleCatalogue.model_validate(
        {"roles": read("target_roles.json")["roles"], "families": read("families.json")["families"]}
    )


@lru_cache(maxsize=1)
def default_role_catalogue() -> RoleCatalogue:
    return load_role_catalogue()
