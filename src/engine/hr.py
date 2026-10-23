"""HR aggregate summary: counts only, small groups suppressed (AGENTS.md privacy rule).

- Group: the employees of one team (or everyone). If the group has fewer than 5 people, nothing
  but the suppression notice is returned.
- Cell: number of people in one evidence state for one skill. Cells of 1–4 people are shown as
  null ("<5"). If exactly one cell in a row is suppressed, the smallest other cell is suppressed
  too, so it cannot be recovered by subtraction from the group size.
- Training demand per scenario: per skill, the number of people who have not demonstrated it,
  counted only when some internal role weights that skill at least 0.05 under that scenario.
No names, no ids, no individual recommendations, no "who should move where".
This reduces but does not eliminate re-identification risk.
"""

from collections.abc import Sequence

from pydantic import BaseModel

from src.contract import (
    SCENARIOS,
    CompanyAssumptions,
    Profile,
    Scenario,
    SkillState,
    SkillStateName,
)
from src.engine import params
from src.engine.catalogue import Catalogue
from src.engine.requirements import scenario_weights

STATE_ORDER: tuple[SkillStateName, ...] = (
    "demonstrated_independently",
    "observed_with_help",
    "self_reported",
    "insufficient_evidence",
)
HR_NOTE = (
    "Aggregates only (synthetic data). Groups and cells under 5 people are suppressed; this "
    "reduces but does not eliminate re-identification risk. HR never sees individual results."
)


class SkillStateCounts(BaseModel):
    skill_id: str
    counts: dict[SkillStateName, int | None]


class DemandItem(BaseModel):
    skill_id: str
    people_without_demonstration: int | None
    max_role_weight: float


class ScenarioDemand(BaseModel):
    scenario: Scenario
    skills: list[DemandItem]


class HrSummary(BaseModel):
    team: str
    group_size: int | None
    min_group_size: int
    suppressed: bool
    skills: list[SkillStateCounts]
    training_demand: list[ScenarioDemand]
    note: str


def suppress_row(counts: dict[SkillStateName, int]) -> dict[SkillStateName, int | None]:
    """Hide cells of 1–4 people, plus one complementary cell when only one would be hidden."""
    hidden = {k for k, v in counts.items() if 0 < v < params.HR_MIN_GROUP_SIZE}
    if len(hidden) == 1:
        others = [k for k in counts if k not in hidden]
        hidden.add(min(others, key=lambda k: (counts[k], STATE_ORDER.index(k))))
    return {k: (None if k in hidden else v) for k, v in counts.items()}


def _suppress_count(value: int) -> int | None:
    return None if 0 < value < params.HR_MIN_GROUP_SIZE else value


def _role_weight_max(
    catalogue: Catalogue, assumptions: CompanyAssumptions, scenario: Scenario
) -> dict[str, float]:
    skill_types = catalogue.skill_types
    best: dict[str, float] = {}
    for role in catalogue.roles.values():
        weights = scenario_weights(role, scenario, assumptions, skill_types).scenario
        for skill_id, weight in weights.items():
            best[skill_id] = max(best.get(skill_id, 0.0), weight)
    return best


def hr_summary(
    team: str | None,
    profiles: Sequence[Profile],
    states_by_user: dict[str, list[SkillState]],
    catalogue: Catalogue,
    assumptions: CompanyAssumptions,
    scenario: Scenario | None = None,
) -> HrSummary:
    members = [p for p in profiles if team is None or p.team == team]
    label = team or "all"
    if len(members) < params.HR_MIN_GROUP_SIZE:
        return HrSummary(
            team=label,
            group_size=None,
            min_group_size=params.HR_MIN_GROUP_SIZE,
            suppressed=True,
            skills=[],
            training_demand=[],
            note=HR_NOTE,
        )
    state_of = {(p.id, s.skill_id): s.state for p in members for s in states_by_user.get(p.id, [])}
    rows = []
    for skill_id in catalogue.skills:
        counts: dict[SkillStateName, int] = dict.fromkeys(STATE_ORDER, 0)
        for person in members:
            counts[state_of.get((person.id, skill_id), "insufficient_evidence")] += 1
        rows.append(SkillStateCounts(skill_id=skill_id, counts=suppress_row(counts)))
    demand = []
    for sc in [scenario] if scenario else list(SCENARIOS):
        weights = _role_weight_max(catalogue, assumptions, sc)
        items = []
        for skill_id, weight in sorted(weights.items(), key=lambda kv: (-kv[1], kv[0])):
            if weight < params.HR_DEMAND_MIN_WEIGHT:
                continue
            gap = sum(
                state_of.get((p.id, skill_id)) != "demonstrated_independently" for p in members
            )
            items.append(
                DemandItem(
                    skill_id=skill_id,
                    people_without_demonstration=_suppress_count(gap),
                    max_role_weight=round(weight, params.WEIGHT_DECIMALS),
                )
            )
        demand.append(ScenarioDemand(scenario=sc, skills=items))
    return HrSummary(
        team=label,
        group_size=len(members),
        min_group_size=params.HR_MIN_GROUP_SIZE,
        suppressed=False,
        skills=rows,
        training_demand=demand,
        note=HR_NOTE,
    )
