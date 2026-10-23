"""Onboarding questionnaire config and the person's held skills (QART_NEXT_STEPS §3).

The questionnaire turns a current role, weekly tasks and tool chips into skill chips at the
default level ("use sometimes"); the person then edits them, and the result is saved as
Profile.preferences.skill_levels. `held_skills` combines those self-rated levels with practice
evidence: a skill shown in a case with help counts as at least "use sometimes", and shown on
your own as "confident". Evidence only raises a level, never lowers it.
"""

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from src.contract import Profile, SkillLevel, SkillState
from src.engine.catalogue import CATALOGUE_DIR

QUESTIONNAIRE_PATH = CATALOGUE_DIR / "questionnaire.json"

# Evidence state -> the level it proves (DECLARED; a self-reported claim proves nothing extra).
EVIDENCE_LEVEL: dict[str, SkillLevel] = {
    "observed_with_help": "sometimes",
    "demonstrated_independently": "confident",
}


class Level(BaseModel):
    id: SkillLevel
    label: str
    value: float


class ToolChip(BaseModel):
    label: str
    skills: list[str]
    exclusive: bool = False  # "None of these": clears the other chips and vice versa


class CurrentRole(BaseModel):
    id: str
    name: str
    family: str | None
    catalogue_role_id: str | None = None  # the matching catalogue role, for the evidence engine
    typical_skills: list[str]


class Task(BaseModel):
    id: str
    label: str
    skills: list[str]
    families: list[str] = []  # shown first for people in these role families


class EducationOption(BaseModel):
    label: str
    level: str  # one of education_order; only the soft min_education note reads it


class Option(BaseModel):
    id: str
    label: str


class Funding(BaseModel):
    employment: list[Option]
    employer_hrd: list[Option]
    budget: list[Option]
    budget_limit_myr: float  # "Up to ~RM200"
    language: list[Option]
    age_band: list[Option]
    malaysian: list[Option]


class Questionnaire(BaseModel):
    funding: Funding
    industries: list[str]
    education: list[EducationOption]
    education_order: list[str]  # lowest to highest
    levels: list[Level]
    default_level: SkillLevel
    tools: list[ToolChip]
    current_roles: list[CurrentRole]
    tasks: list[Task]

    def level_value(self, level: SkillLevel) -> float:
        return next(lv.value for lv in self.levels if lv.id == level)

    def referenced_skill_ids(self) -> set[str]:
        return (
            {k for t in self.tools for k in t.skills}
            | {k for r in self.current_roles for k in r.typical_skills}
            | {k for t in self.tasks for k in t.skills}
        )


def load_questionnaire(path: Path = QUESTIONNAIRE_PATH) -> Questionnaire:
    return Questionnaire.model_validate_json(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def default_questionnaire() -> Questionnaire:
    return load_questionnaire()


def _rank(q: Questionnaire, level: SkillLevel) -> int:
    return [lv.id for lv in q.levels].index(level)


def raise_to(
    levels: dict[str, SkillLevel], skill_id: str, level: SkillLevel, q: Questionnaire
) -> None:
    """Set `skill_id` to `level` unless it is already higher (never downgrade)."""
    current = levels.get(skill_id)
    if current is None or _rank(q, level) > _rank(q, current):
        levels[skill_id] = level


def prefill_levels(
    current_job: str | None, tasks: list[str], tools: list[str], q: Questionnaire
) -> dict[str, SkillLevel]:
    """Skill chips the questionnaire adds before the person edits them (all at the default)."""
    levels: dict[str, SkillLevel] = {}
    roles = {r.id: r for r in q.current_roles}
    task_map = {t.id: t for t in q.tasks}
    tool_map = {t.label: t for t in q.tools}
    skill_ids = list(roles[current_job].typical_skills) if current_job in roles else []
    skill_ids += [k for t in tasks if t in task_map for k in task_map[t].skills]
    skill_ids += [k for t in tools if t in tool_map for k in tool_map[t].skills]
    for skill_id in skill_ids:
        raise_to(levels, skill_id, q.default_level, q)
    return levels


@dataclass(frozen=True)
class HeldSkill:
    skill_id: str
    level: SkillLevel
    value: float  # 0.3 / 0.7 / 1.0 from the questionnaire config
    source: str  # "questionnaire", "practice evidence" or "questionnaire + practice evidence"


def held_skills(
    profile: Profile, states: list[SkillState], q: Questionnaire | None = None
) -> dict[str, HeldSkill]:
    """The person's skills: questionnaire levels, raised (never lowered) by case evidence."""
    q = q or default_questionnaire()
    stated = dict(profile.preferences.skill_levels)
    levels = dict(stated)
    proven: set[str] = set()
    for state in states:
        if (level := EVIDENCE_LEVEL.get(state.state)) is not None:
            before = levels.get(state.skill_id)
            raise_to(levels, state.skill_id, level, q)
            if levels[state.skill_id] != before or state.skill_id not in stated:
                proven.add(state.skill_id)
    held = {}
    for skill_id, level in levels.items():
        source = (
            "questionnaire + practice evidence"
            if skill_id in stated and skill_id in proven
            else "practice evidence"
            if skill_id in proven
            else "questionnaire"
        )
        held[skill_id] = HeldSkill(skill_id, level, q.level_value(level), source)
    return held
