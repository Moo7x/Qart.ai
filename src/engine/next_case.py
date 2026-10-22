"""Pick the next practice or check-in case, with a human-readable `because` (Task A5).

Rule ("your mistakes are your future skills"):
1. Skills with an unresolved miss (an unaided miss with no independent success after it) come
   first: the employee's own mistake is the next lesson. Among them, a skill that already has a
   help-assisted success since the miss goes first, so the loop on that mistake is closed with a
   no-help check-in while it is fresh (golden journey: case_003 → case_006 → checkin_001).
2. Within the two mistake tiers, a skill the employee rated highly at intake goes first: a miss
   on a skill you believe you master is the largest calibration gap (PROJECT_PLAN "reality
   gauge"), e.g. Aina rated adjustments 8/10 and missed one in case_003.
   Then (and over all practised skills if no miss is open) pick the highest
   w·(1 − credit(state)), where w is the skill's scenario weight in the target role (the user's
   top-ranked role unless one is given). Ties: higher provisional-estimate uncertainty p(1−p),
   then skill id.
3. Case type: a check-in once the skill has a help-assisted success since the last miss (test
   whether it holds without help), otherwise a practice case. Among unseen cases containing the
   skill, prefer that type, then the matching scenario_variant, then lower difficulty, then id.
"""

from collections.abc import Sequence

from src.contract import CompanyAssumptions, Event, NextCase, Profile, Scenario, SkillState
from src.engine.catalogue import CaseInfo, Catalogue
from src.engine.recommend import credit, recommend
from src.engine.requirements import scenario_weights
from src.engine.skills import HELP_PHRASE, Observation, observations_for


def _since_last_miss(counted: Sequence[Observation]) -> list[Observation] | None:
    """Counted observations after the most recent unaided miss, or None if there is no miss."""
    misses = [i for i, o in enumerate(counted) if o.is_unaided_miss]
    return list(counted[misses[-1] + 1 :]) if misses else None


def unresolved_miss(counted: Sequence[Observation]) -> Observation | None:
    after = _since_last_miss(counted)
    if after is None or any(o.is_independent_success for o in after):
        return None
    return next(o for o in reversed(counted) if o.is_unaided_miss)


def helped_success_since_miss(counted: Sequence[Observation]) -> Observation | None:
    after = _since_last_miss(counted)
    pool = after if after is not None else list(counted)
    return next((o for o in reversed(pool) if o.outcome == "success" and o.help_level > 0), None)


def _uncertainty(state: SkillState | None) -> float:
    p = state.provisional_estimate if state else 0.0
    return p * (1 - p)


def choose_case(
    skill_id: str,
    prefer_checkin: bool,
    scenario: Scenario,
    cases: Sequence[CaseInfo],
    seen: set[str],
) -> CaseInfo | None:
    candidates = [c for c in cases if skill_id in c.skills and c.id not in seen]
    wanted = "checkin" if prefer_checkin else "practice"
    return min(
        candidates,
        key=lambda c: (c.mode != wanted, c.scenario_variant != scenario, c.difficulty, c.id),
        default=None,
    )


def _because(
    skill_name: str,
    case: CaseInfo,
    miss: Observation | None,
    helped: Observation | None,
    gap_text: str,
) -> str:
    if case.mode == "checkin" and helped is not None:
        return (
            f"You solved '{skill_name}' in {helped.case_id} {HELP_PHRASE[helped.help_level]} "
            f"(help {helped.help_level}); this no-help check-in tests whether it holds on your own."
        )
    if miss is not None:
        found = (
            f", then found it {HELP_PHRASE[miss.help_level]}"
            if miss.outcome == "missed_then_found"
            else ""
        )
        return f"You missed '{skill_name}' in {miss.case_id}{found}. {case.id} practises it again."
    return f"'{skill_name}' is your largest gap here: {gap_text}. {case.id} practises it."


def next_case(
    profile: Profile,
    states: Sequence[SkillState],
    events: Sequence[Event],
    catalogue: Catalogue,
    assumptions: CompanyAssumptions,
    scenario: Scenario,
    cases: Sequence[CaseInfo],
    role_id: str | None = None,
) -> NextCase:
    """The next case for the employee and why (see module docstring for the rule)."""
    by_skill = {s.skill_id: s for s in states}
    target = (
        role_id or recommend(profile, states, catalogue, assumptions, scenario).roles[0].role_id
    )
    role = catalogue.roles[target]
    skill_types = {k: s.type for k, s in catalogue.skills.items()}
    weights = scenario_weights(role, scenario, assumptions, skill_types).scenario
    seen = {e.case_id for e in events}

    claimed = {s.skill_id: s.confidence for s in profile.skills_self_reported}

    def priority(skill_id: str) -> tuple[float, float, str]:
        need = weights.get(skill_id, 0.0) * (1 - credit(by_skill.get(skill_id)))
        return (-need, -_uncertainty(by_skill.get(skill_id)), skill_id)

    def mistake_priority(skill_id: str) -> tuple[float, float, float, str]:
        return (-claimed.get(skill_id, 0.0), *priority(skill_id))

    counted = {
        k: [o for o in observations_for(k, events) if o.counted]
        for k in catalogue.practised_skill_ids
    }
    missed = [k for k, obs in counted.items() if unresolved_miss(obs)]
    closing = [k for k in missed if helped_success_since_miss(counted[k])]
    open_misses = [k for k in missed if k not in closing]
    pool = [
        *sorted(closing, key=mistake_priority),
        *sorted(open_misses, key=mistake_priority),
        *sorted(catalogue.practised_skill_ids, key=priority),
    ]

    for skill_id in dict.fromkeys(pool):
        helped = helped_success_since_miss(counted[skill_id])
        case = choose_case(skill_id, helped is not None, scenario, cases, seen)
        if case is None:
            continue
        state = by_skill.get(skill_id)
        state_name = state.state if state else "insufficient_evidence"
        gap_text = (
            f"weight {weights.get(skill_id, 0.0):.2f} in {role.title} ({scenario}), "
            f"evidence so far: {state_name.replace('_', ' ')}"
        )
        because = _because(
            catalogue.skills[skill_id].name,
            case,
            unresolved_miss(counted[skill_id]),
            helped,
            gap_text,
        )
        return NextCase(case_id=case.id, because=because, skill_id=skill_id)
    return NextCase(case_id=None, because="No unseen case is left for your practised skills.")
