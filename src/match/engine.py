"""Score every destination role for one person under one scenario.

Pure functions: the pack, the person's claimed skill levels and the observed automation shares go
in; ranked roles with every number explained come out. Nothing here calls a model or the network.

    fit = 100 × Σ_k w_k · min(c_k / r_k, 1) ÷ Σ_k w_k

c_k is the person's claimed level of skill k (0 if not stated), r_k the level the role needs and
w_k the weight of that requirement under the scenario. Essential requirements keep their level and
weight in every scenario; other weights shift with the scenario (see `scenario_weight`).

The observed AI-use share behind a shift is task-level where it can be: the O*NET tasks linked to
the skill in this occupation (data/packs/gbs_fa/tasks.yaml), averaged with O*NET importance as the
weight. A skill without task-level evidence uses its occupation's share, and says so.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Literal

from src import params
from src.pack import DestinationRole, Pack, Requirement

Scenario = Literal["moderate", "fast"]
GapColumn = Literal["ready", "bridgeable", "missing", "not_stated"]


@dataclass(frozen=True)
class Evidence:
    """Observed numbers the engine uses, each with where it came from."""

    automation_share: dict[str, float]  # SOC code -> % of conversations that are automation-style
    automation_period: str  # e.g. "2026-05"
    automation_source: str
    task_automation: dict[str, float] = field(default_factory=dict)  # O*NET task id -> same %
    task_period: str = ""
    task_importance: dict[str, float] = field(default_factory=dict)  # task id -> O*NET IM 1–5
    task_importance_source: str = ""


AutomationBasis = Literal["task", "occupation", "none"]


@dataclass(frozen=True)
class TaskEvidence:
    """One O*NET task linked to a requirement, with what is observed about it (None = missing)."""

    task: str
    text: str
    automation_share: float | None
    importance: float | None


@dataclass(frozen=True)
class RequirementScore:
    skill: str
    skill_name: str
    tier: str
    essential: bool
    required: int
    claimed: int | None  # None = not stated
    base_weight: float
    weight: float  # after the scenario shift
    shift_reason: str  # why the weight moved (or did not)
    contribution: float  # fit points this requirement adds
    column: GapColumn
    evidence_pages: list[int]
    automation_share: float | None = None  # the observed share the shift used
    automation_basis: AutomationBasis = "none"
    tasks: list[TaskEvidence] = field(default_factory=list)


@dataclass
class RoleMatch:
    role_id: str
    title: str
    fit: float
    longer_route: bool  # an essential requirement is below its level
    essential_gaps: list[str]
    requirements: list[RequirementScore]
    automation_share: float | None
    soc: str
    gap: dict[GapColumn, list[str]] = field(default_factory=dict)


def required_level(req: Requirement) -> int:
    return params.ROLE_TIER_LEVEL[req.tier]


def requirement_automation(
    pack: Pack, role: DestinationRole, skill_id: str, evidence: Evidence
) -> tuple[float | None, AutomationBasis, list[TaskEvidence]]:
    """Observed automation-style share for one requirement, the level it comes from, its tasks.

    a = Σ_t importance_t × share_t ÷ Σ_t importance_t over the linked tasks with observed use
    (importance 1 when O*NET has none). With no task-level observation: the occupation's share.
    """
    tasks = [
        TaskEvidence(
            task=str(link.task),
            text=link.text,
            automation_share=evidence.task_automation.get(str(link.task)),
            importance=evidence.task_importance.get(str(link.task)),
        )
        for link in pack.tasks_for(role.soc, skill_id)
    ]
    observed = [t for t in tasks if t.automation_share is not None]
    if observed:
        weights = [t.importance or 1.0 for t in observed]
        total = sum(w * (t.automation_share or 0.0) for w, t in zip(weights, observed, strict=True))
        return total / sum(weights), "task", tasks
    occupation = evidence.automation_share.get(role.soc)
    return occupation, ("occupation" if occupation is not None else "none"), tasks


def _basis_text(basis: AutomationBasis, tasks: list[TaskEvidence]) -> str:
    if basis == "task":
        observed = sum(t.automation_share is not None for t in tasks)
        return f"AI use on {observed} of {len(tasks)} linked O*NET tasks"
    if tasks:
        return "AI use for this occupation (its linked tasks have no published task-level data)"
    return "AI use for this occupation (no O*NET task is linked to this skill)"


def scenario_weight(
    req: Requirement,
    ai_role: str,
    scenario: Scenario,
    automation_share: float | None,
    basis: str = "AI use for this occupation",
) -> tuple[float, str]:
    """Weight of one requirement under a scenario, and the sentence that explains it.

    w' = w × (1 + d × s × a)
      w  base weight of the tier (declared)
      d  +1 for skills that complement AI, −1 for routine skills, 0 otherwise (declared per skill)
      s  scenario intensity: how much of the observed automation-style use is assumed to reach
         these tasks within the horizon (declared: moderate 0.5, fast 1.0)
      a  share of AI use that is automation-style (observed): on the skill's linked tasks, or
         for the occupation when no linked task has data (see `requirement_automation`)
    Essential requirements are never shifted.
    """
    base = params.ROLE_TIER_WEIGHT[req.tier]
    if req.essential:
        return base, "Essential: weight fixed in every scenario."
    direction = params.AI_ROLE_DIRECTION[ai_role]
    if direction == 0 or automation_share is None:
        reason = (
            "No shift: neither routine nor AI-complementing."
            if direction == 0
            else "No shift: no observed AI-use data for this skill or its occupation."
        )
        return base, reason
    intensity = params.SCENARIO_INTENSITY[scenario]
    factor = 1 + direction * intensity * automation_share / 100
    verb = "up" if direction > 0 else "down"
    return base * factor, (
        f"Weight {verb} ×{factor:.2f}: {automation_share:.0f}% of {basis} is automation-style "
        f"(observed), and {scenario} adoption assumes {intensity:.0%} of it reaches these tasks."
    )


def gap_column(claimed: int | None, required: int) -> GapColumn:
    if claimed is None:
        return "not_stated"
    if claimed >= required:
        return "ready"
    if claimed == required - 1 and claimed > 0:
        return "bridgeable"
    return "missing"


def score_role(
    pack: Pack,
    role: DestinationRole,
    levels: Mapping[str, int | None],
    scenario: Scenario,
    evidence: Evidence,
) -> RoleMatch:
    share = evidence.automation_share.get(role.soc)
    scored = []
    for req in role.requires:
        skill = pack.skills[req.skill]
        r = required_level(req)
        c = levels.get(req.skill)
        a, basis, tasks = requirement_automation(pack, role, req.skill, evidence)
        weight, reason = scenario_weight(req, skill.ai_role, scenario, a, _basis_text(basis, tasks))
        scored.append((req, skill.name, r, c, weight, reason, a, basis, tasks))
    total_weight = sum(item[4] for item in scored)
    results = []
    for req, name, r, c, weight, reason, a, basis, tasks in scored:
        attained = min((c or 0) / r, 1.0)
        results.append(
            RequirementScore(
                skill=req.skill,
                skill_name=name,
                tier=req.tier,
                essential=req.essential,
                required=r,
                claimed=c,
                base_weight=params.ROLE_TIER_WEIGHT[req.tier],
                weight=weight,
                shift_reason=reason,
                contribution=100 * weight * attained / total_weight,
                column=gap_column(c, r),
                evidence_pages=req.pages,
                automation_share=a,
                automation_basis=basis,
                tasks=tasks,
            )
        )
    essential_gaps = [
        s.skill_name for s in results if s.essential and (s.claimed or 0) < s.required
    ]
    gap: dict[GapColumn, list[str]] = {
        c: [] for c in ("ready", "bridgeable", "missing", "not_stated")
    }
    for s in results:
        gap[s.column].append(s.skill)
    return RoleMatch(
        role_id=role.id,
        title=role.title,
        fit=round(sum(s.contribution for s in results), 1),
        longer_route=bool(essential_gaps),
        essential_gaps=essential_gaps,
        requirements=results,
        automation_share=share,
        soc=role.soc,
        gap=gap,
    )


def rank_roles(
    pack: Pack,
    levels: Mapping[str, int | None],
    scenario: Scenario,
    evidence: Evidence,
    interests: set[str] | None = None,
) -> list[RoleMatch]:
    """Every destination role, best fit first. Interests only re-order near-ties."""
    matches = [
        score_role(pack, role, levels, scenario, evidence)
        for role in pack.destination_roles.values()
    ]
    matches.sort(key=lambda m: -m.fit)
    if interests:
        matches = _order_near_ties(pack, matches, interests)
    return matches


def _interest_overlap(pack: Pack, match: RoleMatch, interests: set[str]) -> int:
    return sum(pack.skills[r.skill].kind in interests for r in match.requirements)


def _order_near_ties(pack: Pack, matches: list[RoleMatch], interests: set[str]) -> list[RoleMatch]:
    """Within groups of roles whose fit differs by less than NEAR_TIE_POINTS, put roles whose
    requirements match the person's interests first. Fit scores themselves never change."""
    ordered: list[RoleMatch] = []
    group: list[RoleMatch] = []
    for match in matches:
        if group and group[0].fit - match.fit >= params.NEAR_TIE_POINTS:
            ordered += sorted(group, key=lambda m: -_interest_overlap(pack, m, interests))
            group = []
        group.append(match)
    ordered += sorted(group, key=lambda m: -_interest_overlap(pack, m, interests))
    return ordered
