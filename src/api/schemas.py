"""Response models for the journey routes: the API contract (docs/PHASE2_PLAN.md §4 C2–C4).

Routes keep building their answers with the existing functions; FastAPI checks each answer
against these models and publishes them in the OpenAPI schema, from which the web app's types
are generated (scripts/openapi.py). A field the producers add but the model lacks is dropped,
which tests/test_api_golden.py catches.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.match.engine import RequirementScore
from src.pack import CurrentRole
from src.pathway.sdg import SdgRole


class Labelled(BaseModel):
    """One sourced statement: an outlook line or why a skill counts for a role."""

    kind: str  # observed · expert · estimate · talentcorp · onet · onet_tech · assumption
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
    requirement_basis: dict[str, Labelled]
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
    destination: str | None
    roles: list[RoleCard]
    sdg_roles: list[SdgRole]
    bands: Bands
