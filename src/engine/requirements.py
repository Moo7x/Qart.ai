"""Role requirement card: O*NET tasks → company allocation (layer B) → skill weights → because.

Weight rule (contract CompanyAssumptions.shift_rule, PROJECT_PLAN §6):
1. base weight of skill k = role.skills[k].base_weight, normalised so the role sums to 1.
2. A skill's base weight is split equally across the role tasks that use it.
3. For each task the scenario gives to `ai_drafts_human_reviews` or `ai`, the fraction f_s
   (50% assistive / 80% agentic, from the assumptions) of every EXECUTION skill's share in that
   task moves to the role's OVERSIGHT skills, pro rata to their base weights.
4. Weight is only moved, never created, so scenario weights still sum to 1.
External evidence never enters this computation; it only informs the assumptions HR approves.
"""

from collections import defaultdict
from dataclasses import dataclass, field

from src.contract import (
    Allocation,
    CardTask,
    CardWeight,
    CompanyAssumptions,
    OutlookLabel,
    RequirementCard,
    Role,
    RoleOutlook,
    Scenario,
    SkillType,
    Snapshot,
    SourceLink,
)
from src.engine import params

ALLOCATION_PHRASE: dict[Allocation, str] = {
    "human": "stays with a human",
    "ai_drafts_human_reviews": "is drafted by AI and reviewed by a human",
    "ai": "moves to AI",
}
PERCENT = (
    100  # shift fractions are shown as whole percentages of weight (an assumption, not a score)
)


@dataclass
class ScenarioWeights:
    """Normalised base and scenario weights per skill, plus what moved and why."""

    base: dict[str, float]
    scenario: dict[str, float]
    lost_in_tasks: dict[str, list[str]] = field(default_factory=dict)
    gained_from_tasks: dict[str, list[str]] = field(default_factory=dict)


def _normalise(weights: dict[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    if total <= 0:
        return {k: 0.0 for k in weights}
    return {k: v / total for k, v in weights.items()}


def scenario_weights(
    role: Role,
    scenario: Scenario,
    assumptions: CompanyAssumptions,
    skill_types: dict[str, SkillType],
) -> ScenarioWeights:
    """Apply the shift rule to one role under one scenario (see module docstring)."""
    base = _normalise({s.skill_id: s.base_weight for s in role.skills})
    weights = dict(base)
    tasks_using: dict[str, list[int]] = defaultdict(list)
    for index, task in enumerate(role.tasks):
        for skill_id in task.skills:
            tasks_using[skill_id].append(index)

    fraction = assumptions.shift_fractions[scenario]
    allocation = assumptions.scenarios[scenario].tasks
    oversight = [k for k in base if skill_types[k] == "oversight"]
    oversight_base_total = sum(base[k] for k in oversight)
    lost: dict[str, list[str]] = defaultdict(list)
    gained: dict[str, list[str]] = defaultdict(list)

    for task in role.tasks:
        if allocation[task.workflow_task] == "human" or oversight_base_total <= 0:
            continue
        for skill_id in task.skills:
            if skill_types[skill_id] != "execution":
                continue
            moved = fraction * base[skill_id] / len(tasks_using[skill_id])
            weights[skill_id] -= moved
            lost[skill_id].append(task.workflow_task)
            for target in oversight:
                weights[target] += moved * base[target] / oversight_base_total
                if task.workflow_task not in gained[target]:
                    gained[target].append(task.workflow_task)
    return ScenarioWeights(base, weights, dict(lost), dict(gained))


def _assumption_tag(assumptions: CompanyAssumptions) -> str:
    return f"assumption v{assumptions.version}"


def _because(
    skill_id: str,
    scenario: Scenario,
    weights: ScenarioWeights,
    assumptions: CompanyAssumptions,
    skill_types: dict[str, SkillType],
) -> str:
    tag = _assumption_tag(assumptions)
    allocation = assumptions.scenarios[scenario].tasks
    pct = round(assumptions.shift_fractions[scenario] * PERCENT)
    if skill_id in weights.lost_in_tasks:
        descriptions = assumptions.task_descriptions
        moves = "; ".join(
            f"'{descriptions.get(task, task)}' {ALLOCATION_PHRASE[allocation[task]]}"
            for task in dict.fromkeys(weights.lost_in_tasks[skill_id])
        )
        return (
            f"{scenario}: {moves} → {pct}% of this execution skill's weight there shifts to "
            f"oversight skills ({tag})"
        )
    if skill_id in weights.gained_from_tasks:
        tasks = ", ".join(weights.gained_from_tasks[skill_id])
        return (
            f"{scenario}: oversight skill gains weight shifted from execution work in tasks the AI "
            f"drafts or does ({tasks}) ({tag})"
        )
    if skill_types[skill_id] == "oversight":
        return f"{scenario}: oversight skill; no task in this role is handed to AI ({tag})"
    return f"{scenario}: the tasks using this skill stay with a human ({tag})"


def evidence_links(role: Role, snapshot: Snapshot | None) -> list[SourceLink]:
    """Layer-A signals about the role's O*NET occupations (context for the assumptions only)."""
    if snapshot is None:
        return []
    socs = {basis.code.split(".")[0] for basis in role.based_on}
    links = []
    for signal in snapshot.signals:
        soc = next((s for s in socs if signal.entity.startswith(f"SOC {s}")), None)
        if soc is None:
            continue
        value = round(signal.value, params.SIGNAL_DECIMALS)
        links.append(
            SourceLink(
                label=(
                    f"AEI {snapshot.period}, {signal.geo or snapshot.geo}, SOC {soc} "
                    f"{signal.metric} {value} (release {snapshot.release_date}, CC-BY)"
                ),
                url=snapshot.url,
                kind="evidence",
            )
        )
    return links


def task_weights(role: Role) -> list[float]:
    """Each role task's share of base weight: Σ over its skills of base_k / (tasks using k)."""
    base = _normalise({s.skill_id: s.base_weight for s in role.skills})
    uses: dict[str, int] = defaultdict(int)
    for task in role.tasks:
        for skill_id in task.skills:
            uses[skill_id] += 1
    return [sum(base[k] / uses[k] for k in task.skills) for task in role.tasks]


def role_outlook(
    role: Role,
    scenario: Scenario,
    assumptions: CompanyAssumptions,
    skill_types: dict[str, SkillType],
) -> RoleOutlook:
    """Share of task weight handled by AI, oversight share of skill weight, and a label.

    ai_handled_share = Σ task weight allocated to ai / ai_drafts_human_reviews ÷ Σ task weight
    oversight_share  = Σ scenario weight of oversight skills (scenario weights sum to 1)
    label: "being transformed" if ai_handled_share ≥ 0.5; else "AI-era role" if
           oversight_share ≥ 0.6; else "stable" (thresholds in params.py).
    """
    allocation = assumptions.scenarios[scenario].tasks
    weights = task_weights(role)
    total = sum(weights)
    handled = [
        (w, t)
        for w, t in zip(weights, role.tasks, strict=True)
        if allocation[t.workflow_task] != "human"
    ]
    ai_share = sum(w for w, _ in handled) / total if total > 0 else 0.0
    scenario_w = scenario_weights(role, scenario, assumptions, skill_types).scenario
    oversight = sum(w for k, w in scenario_w.items() if skill_types[k] == "oversight")
    label: OutlookLabel = "stable"
    if ai_share >= params.OUTLOOK_TRANSFORMED_AI_SHARE:
        label = "being transformed"
    elif oversight >= params.OUTLOOK_AI_ERA_OVERSIGHT_SHARE:
        label = "AI-era role"
    tasks = ", ".join(dict.fromkeys(t.workflow_task for _, t in handled)) or "none"
    ai_rounded = round(ai_share, params.OUTLOOK_DECIMALS)
    oversight_rounded = round(oversight, params.OUTLOOK_DECIMALS)
    because = (
        f"{scenario}: {ai_rounded:.2f} of this role's task weight is done or drafted by AI "
        f"({tasks}); {oversight_rounded:.2f} of its skill weight is oversight "
        f"({_assumption_tag(assumptions)})"
    )
    return RoleOutlook(
        ai_handled_share=ai_rounded,
        oversight_share=oversight_rounded,
        label=label,
        because=because,
        basis=params.OUTLOOK_BASIS,
    )


def requirement_card(
    role: Role,
    scenario: Scenario,
    assumptions: CompanyAssumptions,
    skill_types: dict[str, SkillType],
    snapshot: Snapshot | None = None,
) -> RequirementCard:
    """The requirement card: tasks → allocation → weights → because (assumption + evidence)."""
    weights = scenario_weights(role, scenario, assumptions, skill_types)
    allocation = assumptions.scenarios[scenario].tasks
    tasks = [
        CardTask(
            task=t.task,
            onet=t.onet,
            allocation=allocation[t.workflow_task],
            workflow_task=t.workflow_task,
        )
        for t in role.tasks
    ]
    ordered = sorted(weights.scenario, key=lambda k: (-weights.scenario[k], k))
    card_weights = [
        CardWeight(
            skill_id=k,
            base=round(weights.base[k], params.WEIGHT_DECIMALS),
            scenario=round(weights.scenario[k], params.WEIGHT_DECIMALS),
            because=_because(k, scenario, weights, assumptions, skill_types),
        )
        for k in ordered
    ]
    assumption_text = (
        f"Company assumptions v{assumptions.version} ({assumptions.updated_by}): "
        f"{assumptions.shift_rule}."
    )
    if assumptions.based_on_snapshot:
        assumption_text += f" Reviewed against snapshot {assumptions.based_on_snapshot}."
    return RequirementCard(
        tasks=tasks,
        weights=card_weights,
        evidence=evidence_links(role, snapshot),
        assumption=assumption_text,
        outlook=role_outlook(role, scenario, assumptions, skill_types),
    )
