"""Practice tasks (data/packs/gbs_fa/practice.yaml): how a skill moves above what study reaches.

Study takes a skill to STUDY_MAX_LEVEL ("aware") at most; levels 3 ("working") and 4
("proficient") come from work done. Each task is a suggestion to agree with a manager, with a week
range that is a declared estimate, and `show_by`: what the person describes in a progress check.
Loading fails loudly if a required skill lacks a task for level 3 or 4, a week range is reversed,
a task has no basis, or a skill id is not in the pack.
"""

from functools import cache

import yaml
from pydantic import BaseModel

from src.evidence.field import PACK_DIR
from src.levels import Basis, required_skills
from src.pack import Pack, PackError, load_pack

PRACTICE_FILE = PACK_DIR / "practice.yaml"
PRACTICE_LEVELS = (3, 4)  # levels a practice task leads to; 5 sets direction, not a task


class PracticeTask(BaseModel):
    text: str
    weeks_low: int
    weeks_high: int
    show_by: str
    status: str
    basis: list[Basis]


class Practice(BaseModel):
    checked: str
    skills: dict[str, dict[int, PracticeTask]]

    def task(self, skill_id: str, level: int) -> PracticeTask | None:
        return self.skills.get(skill_id, {}).get(level)


def _check(pack: Pack, practice: Practice) -> None:
    problems = []
    for skill_id in required_skills(pack):
        if tuple(sorted(practice.skills.get(skill_id, {}))) != PRACTICE_LEVELS:
            problems.append(f"{skill_id}: needs a task for levels 3 and 4")
    for skill_id, tasks in practice.skills.items():
        if skill_id not in pack.skills:
            problems.append(f"{skill_id}: not a pack skill")
        for level, task in tasks.items():
            if not 0 < task.weeks_low <= task.weeks_high:
                problems.append(f"{skill_id} {level}: weeks must be positive and low ≤ high")
            if not task.basis:
                problems.append(f"{skill_id} {level}: needs at least one cited basis")
    if problems:
        raise PackError("practice.yaml: " + "; ".join(problems))


def parse_practice(pack: Pack, raw: dict[str, object]) -> Practice:
    practice = Practice.model_validate(raw)
    _check(pack, practice)
    return practice


@cache
def load_practice() -> Practice:
    raw = yaml.safe_load(PRACTICE_FILE.read_text(encoding="utf-8"))
    return parse_practice(load_pack(), raw)
