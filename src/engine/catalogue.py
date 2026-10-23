"""Load the static catalogues (catalogue/*.json) into typed objects.

The catalogue is read-only reference data: skills, O*NET-based roles, free courses, the SDG map
and the version-1 company assumptions. Later assumption versions live in the store (HR edits).
"""

import json
from dataclasses import dataclass, field
from functools import cached_property, lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from src.contract import CaseMode, CompanyAssumptions, Course, Role, Scenario, SkillType

REPO_ROOT = Path(__file__).resolve().parents[2]
CATALOGUE_DIR = REPO_ROOT / "catalogue"
CASE_INDEX_PATH = REPO_ROOT / "data" / "case_index.json"  # planned fallback (Person A)
# Person B's case index (cases/ is B's folder; Person A only reads it). Each entry has
# id, mode, difficulty, scenario_variant, practised_skills; no ground truth.
B_CASE_INDEX_PATH = REPO_ROOT / "cases" / "index.json"


class LearnHours(BaseModel):
    """ASSUMPTION (team estimates): hours from none to "use sometimes", then to "confident"."""

    to_basic: float = Field(gt=0)
    to_confident: float = Field(gt=0)


class SkillInfo(BaseModel):
    """One entry of the canonical skill vocabulary (catalogue/skills.json, QART_NEXT_STEPS §2)."""

    id: str
    name: str
    practised: bool
    description: str = ""
    # Execution vs oversight drives the old requirement-card weights; only evidence skills need it.
    type: SkillType | None = None
    type_reason: str = ""
    category: str = ""
    evidence_tracked: bool = True  # an evidence state is kept (cases, My skills, HR)
    learn_hours: LearnHours | None = None
    trend_tracked: bool = False  # has Hacker News patterns for the Skills Radar
    patterns: list[str] = []
    case_sensitive_patterns: list[str] = []
    market_name: str | None = None  # label in the radar when it differs from `name`
    # DECLARED: how much of the skill AI can increasingly do on its own (fast scenario only).
    ai_exposure: Literal["high", "medium", "low"] | None = None
    prerequisites: list[str] = []  # DECLARED: planned after these skills (pathway.md §4.4)
    learn_hours_source: Literal["estimate", "derived"] = "estimate"


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
    # `_about` in the file says the mapping is the team's declared judgment, not external
    # evidence; the UI shows it, so it is exposed as `about`.
    model_config = ConfigDict(populate_by_name=True)

    about: str = Field(default="", validation_alias="_about")
    retrieved: str
    targets: list[SdgTarget]
    roles: dict[str, SdgLink]
    skills: dict[str, SdgLink]


class CaseInfo(BaseModel):
    """Case metadata Person A may read (never ground_truth; see CONTRACT_QUESTIONS Q4).

    `skills` are the skills a case practises. They are for targeting only and must never be shown
    to the employee before a decision (that would leak the answer).
    """

    id: str
    title: str | None = None
    mode: CaseMode
    scenario_variant: Scenario
    difficulty: int
    skills: list[str]


@dataclass(frozen=True)
class Catalogue:
    skills: dict[str, SkillInfo]  # evidence-tracked skills only (states, cases, HR)
    roles: dict[str, Role]
    courses: dict[str, Course]
    sdg: SdgMap
    assumptions_v1: CompanyAssumptions
    vocabulary: dict[str, SkillInfo] = field(default_factory=dict)  # every skill in the app

    def skill_type(self, skill_id: str) -> SkillType:
        skill_type = self.skills[skill_id].type
        if skill_type is None:
            raise ValueError(f"evidence skill {skill_id} has no execution/oversight type")
        return skill_type

    @cached_property
    def skill_types(self) -> dict[str, SkillType]:
        """Execution/oversight per evidence skill, for the requirement-card weights.

        Cached: scoring reads it per role and scenario, and the catalogue never changes.
        """
        return {k: self.skill_type(k) for k in self.skills}

    @property
    def practised_skill_ids(self) -> list[str]:
        return [skill.id for skill in self.skills.values() if skill.practised]


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_catalogue(directory: Path = CATALOGUE_DIR) -> Catalogue:
    """Read and validate every catalogue file in `directory`."""
    vocabulary = [
        SkillInfo.model_validate(s) for s in _read_json(directory / "skills.json")["skills"]
    ]
    skills = [s for s in vocabulary if s.evidence_tracked]
    roles = [Role.model_validate(r) for r in _read_json(directory / "roles.json")["roles"]]
    courses = [Course.model_validate(c) for c in _read_json(directory / "courses.json")["courses"]]
    return Catalogue(
        skills={s.id: s for s in skills},
        vocabulary={s.id: s for s in vocabulary},
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


def _case_entries(data: Any) -> list[dict[str, Any]]:
    """Accept either a bare list or {"cases": [...]}."""
    entries: list[dict[str, Any]] = data["cases"] if isinstance(data, dict) else data
    return entries


def _to_case_info(entry: dict[str, Any]) -> CaseInfo:
    # B's index names the skill list `practised_skills`; our planned index uses `skills`.
    skills = entry.get("practised_skills", entry.get("skills", []))
    return CaseInfo.model_validate({**entry, "skills": skills})


def load_case_index(
    primary: Path = B_CASE_INDEX_PATH, fallback: Path = CASE_INDEX_PATH
) -> list[CaseInfo]:
    """Case metadata in file order: Person B's cases/index.json if it exists, else the planned
    data/case_index.json."""
    path = primary if primary.exists() else fallback
    return [_to_case_info(e) for e in _case_entries(_read_json(path))]


def case_index_source(primary: Path = B_CASE_INDEX_PATH) -> str:
    return "cases/index.json (Person B)" if primary.exists() else "data/case_index.json (planned)"


@lru_cache(maxsize=1)
def default_case_index() -> tuple[CaseInfo, ...]:
    return tuple(load_case_index())


def checkin_cases_by_skill(cases: tuple[CaseInfo, ...] | list[CaseInfo]) -> dict[str, list[str]]:
    """Check-in case ids per skill, used for SkillState.next_to_confirm."""
    result: dict[str, list[str]] = {}
    for case in cases:
        if case.mode == "checkin":
            for skill_id in case.skills:
                result.setdefault(skill_id, []).append(case.id)
    return result
