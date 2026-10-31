"""Level descriptions (docs/PHASE2_PLAN.md §4 C1): the 0–5 scale and the "I can…" sentences.

A person picks the highest sentence that is true for their work, so a level means something
observable. Stored levels keep their numbers (§1 decision 2); this file only says what each number
means. Loading fails loudly if the scale is not 0–5 with six labels, a skill has a gap in its five
sentences, or a skill id is not in the pack.

Run `python -m src.levels --missing` to list the required skills without a full set of sentences.
"""

import sys
from functools import cache
from typing import Literal

import yaml
from pydantic import BaseModel

from src.evidence.field import PACK_DIR
from src.pack import Pack, PackError, load_pack

LEVELS_FILE = PACK_DIR / "levels.yaml"
SCALE_LEVELS = (0, 1, 2, 3, 4, 5)
ANCHOR_LEVELS = (1, 2, 3, 4, 5)  # level 0 is "none of these"; it has no sentence


class ScaleLevel(BaseModel):
    level: int
    label: str
    meaning: str


class Basis(BaseModel):
    title: str
    url: str
    read: str


class SkillLevels(BaseModel):
    status: Literal["draft", "reviewed"]
    basis: list[Basis]
    anchors: dict[int, str]


class Levels(BaseModel):
    checked: str
    scale: list[ScaleLevel]
    rules: list[str]
    skills: dict[str, SkillLevels]

    def anchor(self, skill_id: str, level: int) -> str:
        return self.skills[skill_id].anchors[level]

    def labels(self) -> list[str]:
        return [s.label for s in self.scale]


def required_skills(pack: Pack) -> list[str]:
    return sorted({r.skill for role in pack.destination_roles.values() for r in role.requires})


def missing(pack: Pack, levels: "Levels") -> list[str]:
    """Required skills without a sentence for every level 1–5."""
    return [
        s
        for s in required_skills(pack)
        if s not in levels.skills or tuple(sorted(levels.skills[s].anchors)) != ANCHOR_LEVELS
    ]


def _check(pack: Pack, levels: Levels) -> None:
    problems = []
    if tuple(s.level for s in levels.scale) != SCALE_LEVELS:
        problems.append("scale must list levels 0–5 in order")
    for skill_id, skill in levels.skills.items():
        if skill_id not in pack.skills:
            problems.append(f"{skill_id}: not a pack skill")
        if tuple(sorted(skill.anchors)) != ANCHOR_LEVELS:
            problems.append(f"{skill_id}: needs one sentence for each level 1–5")
        if not skill.basis:
            problems.append(f"{skill_id}: needs at least one cited basis")
    if problems:
        raise PackError("levels.yaml: " + "; ".join(problems))


def parse_levels(pack: Pack, raw: dict[str, object]) -> Levels:
    levels = Levels.model_validate(raw)
    _check(pack, levels)
    return levels


@cache
def load_levels() -> Levels:
    raw = yaml.safe_load(LEVELS_FILE.read_text(encoding="utf-8"))
    return parse_levels(load_pack(), raw)


def main(argv: list[str]) -> int:
    if argv != ["--missing"]:
        print("usage: python -m src.levels --missing")
        return 2
    for skill_id in missing(load_pack(), load_levels()):
        print(skill_id)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
