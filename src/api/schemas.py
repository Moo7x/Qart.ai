"""Response models for the journey routes: the API contract (docs/PHASE2_PLAN.md §4 C2–C4).

Routes keep building their answers with the existing functions; FastAPI checks each answer
against these models and publishes them in the OpenAPI schema, from which the web app's types
are generated (scripts/openapi.py). A field the producers add but the model lacks is dropped,
which tests/test_api_golden.py catches.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.evidence.signals import Signal
from src.match.engine import RequirementScore
from src.pack import CurrentRole, FitCheck
from src.pathway.planner import PracticeStep
from src.pathway.sdg import SdgRole


class Labelled(BaseModel):
    """One sourced statement: an outlook line or why a skill counts for a role."""

    kind: str  # observed · expert · estimate · talentcorp · onet · onet_tech · assumption
    text: str
    source: str


class SkillBasis(BaseModel):
    """Why a skill counts for a role (src/match/basis.py)."""

    kind: Literal["talentcorp", "onet", "onet_tech", "assumption", "ai_trend"]
    text: str
    source: str


class Meters(BaseModel):
    coverage: float
    essentials_ready: bool
    essentials_below: list[str]
    essentials_unstated: list[str]
    completeness: float
    stated: int
    requirements: int


class FitRangeOut(BaseModel):
    low: float
    high: float
    basis: str


class Component(BaseModel):
    skill: str
    skill_name: str
    weight: float
    claimed: int | None
    required: int
    points: float
    evidenced: bool
    evidence: str
    source: str


class RaiseOption(BaseModel):
    skill: str
    skill_name: str
    from_level: int | None
    to_level: int
    points: float
    via: Literal["study", "practice", "check"]


class Pay(BaseModel):
    group: str
    group_title: str
    year: str
    median: float
    mean: float | None
    overall_median: float | None
    unit: str
    kind: Literal["observed"]
    source: str
    fetched_at: str
    cited_span: str
    note: str


class SdgRef(BaseModel):
    target: str
    title: str
    how: str


class RoleForecast(BaseModel):
    """Where a role is heading (src/forecast/industry.py), an estimate with its reasons."""

    category: str
    label: str
    meaning: str
    reasons: list[str]
    change_pp: float | None
    critical: bool | None
    ai_use: float | None
    kind: str


class RoleCard(BaseModel):
    """C2: one ranked role with its fit, range, band, components and what would raise it."""

    model_config = ConfigDict(populate_by_name=True)

    role_id: str
    title: str
    fit: float
    longer_route: bool
    essential_gaps: list[str]
    requirements: list[RequirementScore]
    automation_share: float | None
    soc: str
    gap: dict[str, list[str]]
    impact: str
    outlook: list[Labelled]
    meters: Meters
    fit_range: FitRangeOut
    band: str
    band_basis: str
    components: list[Component]
    raise_: list[RaiseOption] = Field(alias="raise")
    essentials_short: list[str]
    pay: Pay | None
    listed_transition: bool
    effort_hours: float
    effort_weeks: int
    uncovered: list[str]
    sdgs: list[SdgRef]
    requirement_basis: dict[str, SkillBasis]
    in_demand: list[str]  # skill ids TalentCorp names as in demand (expert view)
    forecast: RoleForecast | None = None
    direction: str = "stretch"  # "adjacent" or "stretch" (src/match/directions.py)
    related_tier: int | None = None  # 0 same occupation, 1-3 O*NET relatedness tier
    direction_score: float = 0.0  # fit x outlook factor: the order roles are shown in
    serves_goals: list[str]


class EvidenceInfo(BaseModel):
    source: str
    period: str
    occupations: int


class Bands(BaseModel):
    thresholds: dict[str, float]
    below: str
    kind: Literal["assumption"]


class MatchesOut(BaseModel):
    scenario: str
    scenario_label: str
    horizon_years: int
    intensity: float
    evidence: EvidenceInfo
    current_role: CurrentRole | None
    current_impact: str | None
    current_forecast: RoleForecast | None = None
    destination: str | None
    sdg_goals: list[str] = []
    roles: list[RoleCard]
    sdg_roles: list[SdgRole]
    bands: Bands


# --- /tracks: the plan as AI basics, without AI and with AI, and the route comparison --------


class TrackCourse(BaseModel):
    id: str
    title: str
    provider: str
    url: str
    minutes: int
    level: str
    planned: bool
    done: bool
    fit_check: FitCheck | None


class TrackVideo(BaseModel):
    id: str
    title: str
    channel: str
    url: str
    minutes: int
    published: str


class TrackArticle(BaseModel):
    id: str
    title: str
    publisher: str
    url: str
    is_article: bool = True  # False: a web page or a page that refuses readers (no agent)


class BasicsItem(BaseModel):
    """An AI-basics course or video carried inside a step (prompting, responsible use)."""

    kind: Literal["course", "video"]
    topic: str
    title: str
    provider: str
    url: str
    minutes: int


class AiResource(BaseModel):
    """A checked resource on doing a skill's work with AI (src/collectors/ai_resources.py)."""

    kind: Literal["course", "video"]
    id: str
    title: str
    provider: str
    url: str
    minutes: int
    published: str
    skill_quote: str
    ai_quote: str
    score: float


class TrackNode(BaseModel):
    """A skill stop (skill nodes also carry study_after, practice and why; AI-basics topic
    stops do not, and the answer leaves those keys out)."""

    id: str
    title: str
    skill: str | None
    essential: bool
    now: int | None
    required: int | None
    after: int | None
    courses: list[TrackCourse]
    videos: list[TrackVideo]
    articles: list[TrackArticle]
    status: Literal["done", "open", "no_course"]
    study_after: int | None = None
    practice: list[PracticeStep] | None = None
    why: SkillBasis | None = None
    # The one path (src/pathway/reskill.py): basics, adapt a held skill, or learn a gap skill.
    mode: Literal["basics", "oversee", "use_ai", "learn"] | None = None
    ai_use: float | None = None  # effective automation-style AI use on the skill's tasks
    ai_basis: str | None = None  # observed, predicted, mixed, occupation or none
    ai_resources: list[AiResource] | None = None  # adapt steps: doing the skill with AI
    ai_tasks: list[str] | None = None  # the AI-affected tasks those resources were ranked for
    basics: list[BasicsItem] | None = None  # adapt steps without AI resources: AI basics inside


class Track(BaseModel):
    id: Literal["ai_basics", "without_ai", "with_ai", "path"]
    title: str
    why: str
    nodes: list[TrackNode]
    shown: bool | None = None
    reason: str | None = None


class RouteMetrics(BaseModel):
    hours: float
    weeks: int
    courses: int
    fit_after: dict[str, float]
    points_per_10h: dict[str, float]
    essentials_unmet: list[str]
    ai_basics_hours: float | None = None
    plan_hours: float | None = None


class RouteComparison(BaseModel):
    fit_now: dict[str, float]
    without_ai: RouteMetrics
    with_ai: RouteMetrics
    note: str


class TracksOut(BaseModel):
    role_id: str
    role_title: str
    scenario: str
    weekly_hours: float
    tracks: list[Track]
    path: Track | None = None
    comparison: RouteComparison
    resources_checked: str
    courses_checked: str


class Strength(BaseModel):
    skill: str
    name: str
    level: int | None
    ai_use: float | None
    ai_basis: str
    text: str


class ReskillOut(BaseModel):
    """GET /reskill: the person's job's AI-era path, shown before a destination is chosen."""

    scenario: str
    current_role: str | None
    current_forecast: RoleForecast | None
    track: Track
    strengths: list[Strength]
    destination: str | None


# --- /future: today against after the plan, in both scenarios -------------------------------


class FutureRole(BaseModel):
    role_id: str
    title: str
    fit: float


class FutureSkill(BaseModel):
    skill: str
    name: str
    required: int
    now: int | None
    after: int
    essential: bool


class FutureScenario(BaseModel):
    roles_now: list[FutureRole]
    roles_after: list[FutureRole]
    fit_now: float
    fit_after: float
    hours: float
    weeks: int
    skills: list[FutureSkill]
    sdg_targets: list[str]
    uncovered: list[str]


class SkillNow(BaseModel):
    skill: str
    name: str
    level: int


class InDemand(BaseModel):
    ai_digital: list[str]
    green: list[str]


class Market(BaseModel):
    source: str
    published: str
    in_demand: InDemand
    in_demand_page: int
    emerging_roles: list[str]
    emerging_page: int


class RoleRef(BaseModel):
    id: str
    title: str


class FutureOut(BaseModel):
    skills_now: list[SkillNow]
    market: Market
    destination: RoleRef
    current_role: str | None
    situation: str
    years_experience: float | None
    scenarios: dict[str, FutureScenario]


# --- /radar: the role's skills for this person, and their field's signals -------------------


class AiUse(BaseModel):
    automation_share: float | None
    basis: str
    tasks_observed: int
    tasks_linked: int


class RadarAxis(BaseModel):
    skill: str
    name: str
    kind: str
    essential: bool
    claimed: int | None
    required: int
    after: int
    emphasis: Literal["rising", "weakening", "stable", "fixed"]
    weight_factor: float
    reason: str
    ai_use: AiUse | None
    in_demand: bool | None


class RadarOut(BaseModel):
    role_id: str
    title: str
    chosen: bool
    fit: float
    fit_after: float
    axes: list[RadarAxis]
    field_signals: list[Signal]
    scenario: str
    scenario_label: str
