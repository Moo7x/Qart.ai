"""Load the static catalogues (catalogue/*.json) into typed objects.

The catalogue is read-only reference data: skills, O*NET-based roles, free courses, the SDG map
and the version-1 company assumptions. Later assumption versions live in the store (HR edits).
"""

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from src.contract import CompanyAssumptions, Course, Role, SkillType

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOGUE_DIR = REPO_ROOT / "catalogue"


class SkillInfo(BaseModel):
    id: str
    name: str
    practised: bool
    type: SkillType
    description: str
    type_reason: str


class SdgTarget(BaseModel):
    id: str
    main: bool
    goal: int
    title: str
    url: str
    rationale: str


class SdgLink(BaseModel):
    targets: list[str]
    rationale: str


class SdgMap(BaseModel):
    retrieved: str
    targets: list[SdgTarget]
    roles: dict[str, SdgLink]
    skills: dict[str, SdgLink]


@dataclass(frozen=True)
class Catalogue:
    skills: dict[str, SkillInfo]
    roles: dict[str, Role]
    courses: dict[str, Course]
    sdg: SdgMap
    assumptions_v1: CompanyAssumptions

    def skill_type(self, skill_id: str) -> SkillType:
        return self.skills[skill_id].type

    @property
    def practised_skill_ids(self) -> list[str]:
        return [skill.id for skill in self.skills.values() if skill.practised]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalogue(directory: Path = CATALOGUE_DIR) -> Catalogue:
    """Read and validate every catalogue file in `directory`."""
    skills = [SkillInfo.model_validate(s) for s in _read_json(directory / "skills.json")["skills"]]
    roles = [Role.model_validate(r) for r in _read_json(directory / "roles.json")["roles"]]
    courses = [Course.model_validate(c) for c in _read_json(directory / "courses.json")["courses"]]
    return Catalogue(
        skills={s.id: s for s in skills},
        roles={r.id: r for r in roles},
        courses={c.id: c for c in courses},
        sdg=SdgMap.model_validate(_read_json(directory / "sdg_map.json")),
        assumptions_v1=CompanyAssumptions.model_validate(
            _read_json(directory / "company_assumptions.json")
        ),
    )


@lru_cache(maxsize=1)
def default_catalogue() -> Catalogue:
    """The repository catalogue, loaded once per process."""
    return load_catalogue()
