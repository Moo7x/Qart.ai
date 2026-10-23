"""Role recommender (contract Recommendation v2, PROJECT_PLAN §6).

Display: `score` is clamped at 0 (the UI never shows negative scores) while ordering uses the
unclamped value; fit = (score + 0.15·effort) / 0.85 ∈ [0, 1]; time_to_ready = hours to close gaps
and weeks at the employee's budget; the top two roles get close_match when their unclamped scores
differ by less than CLOSE_MATCH_THRESHOLD.

For employee u, role r, scenario s (weights w from the requirement card, summing to 1):
  coverage   = Σ_k w_k · credit(state_k) / Σ_k w_k
               credit: demonstrated 1.0 · observed_with_help 0.5 · self_reported 0.2
                       · insufficient_evidence 0
  confidence = Σ_k w_k · [counted_events_k ≥ 2] / Σ_k w_k
  interest   = |interests ∩ role tags| / |interests|   (0 when no interests are given)
  effort     = min(1, hours to close gaps / (weekly_hours × H))            ← a PENALTY
               H = 12 weeks, or the person's own timeframe in weeks when set (v2.2)
  score      = 0.55·coverage + 0.20·confidence + 0.10·interest − 0.15·effort
The score is a suitability indicator, not a probability. Demographic fields are never read.
"""

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, replace

from src.contract import (
    ChangedSince,
    CompanyAssumptions,
    Course,
    Factors,
    GapItem,
    OutlookChange,
    Profile,
    RankChange,
    Recommendation,
    Role,
    RoleRecommendation,
    Scenario,
    SkillState,
    Snapshot,
    SourceLink,
    TimeToReady,
)
from src.engine import params
from src.engine.catalogue import Catalogue
from src.engine.requirements import requirement_card, scenario_weights

ASSUMPTIONS_URL = "/api/assumptions"


@dataclass(frozen=True)
class ScoreWeights:
    """The four declared formula weights (params.py); varied only by the sensitivity check."""

    coverage: float = params.SCORE_WEIGHT_COVERAGE
    confidence: float = params.SCORE_WEIGHT_CONFIDENCE
    interest: float = params.SCORE_WEIGHT_INTEREST
    effort: float = params.SCORE_WEIGHT_EFFORT

    @property
    def formula(self) -> str:
        return (
            f"{self.coverage:.2f}*coverage + {self.confidence:.2f}*confidence + "
            f"{self.interest:.2f}*interest - {self.effort:.2f}*effort"
        )

    def fit(self, factors: Factors) -> float:
        """The score without the effort penalty, rescaled to 0–1."""
        positive = self.coverage + self.confidence + self.interest
        return (
            self.coverage * factors.coverage
            + self.confidence * factors.confidence
            + self.interest * factors.interest
        ) / positive

    def score(self, factors: Factors) -> float:
        return (
            self.coverage * factors.coverage
            + self.confidence * factors.confidence
            + self.interest * factors.interest
            - self.effort * factors.effort
        )


DEFAULT_WEIGHTS = ScoreWeights()


def credit(state: SkillState | None) -> float:
    return params.STATE_CREDIT[state.state] if state else 0.0


def hours_to_learn(skill_id: str, practised: bool, courses: Iterable[Course]) -> float:
    """Hours of the shortest resource for a skill: an in-app practice bundle for practised skills,
    otherwise the shortest course (verified ones first). 0 when nothing covers the skill."""
    if practised:
        return params.PRACTICE_BUNDLE_HOURS
    covering = [c for c in courses if skill_id in c.skills]
    verified = [c for c in covering if c.verified] or covering
    return min((c.hours for c in verified), default=0.0)


def gap_hours(
    weights: dict[str, float], states: dict[str, SkillState], catalogue: Catalogue
) -> float:
    """Hours to close the gaps: Σ over weighted skills of (1 − credit) × shortest resource."""
    return sum(
        (1 - credit(states.get(k)))
        * hours_to_learn(k, catalogue.skills[k].practised, catalogue.courses.values())
        for k, w in weights.items()
        if w > 0
    )


def eligible_roles(profile: Profile, catalogue: Catalogue) -> list[str]:
    """Roles the person's chosen direction allows for their path (all roles without one).

    grow → the current role · adjacent → other roles sharing at least one skill with it ·
    switch → every role except the current one (the catalogue holds finance-related roles
    only). Falls back to all roles if the rule leaves none, so a path always exists.
    """
    every = sorted(catalogue.roles)
    direction = profile.preferences.direction
    current = profile.current_role_id
    if direction is None or current not in catalogue.roles:
        return every
    if direction == "grow":
        return [current]
    others = [r for r in every if r != current]
    if direction == "adjacent":
        mine = {s.skill_id for s in catalogue.roles[current].skills}
        others = [r for r in others if mine & {s.skill_id for s in catalogue.roles[r].skills}]
    return others or every


DIRECTION_LABEL = {
    "grow": "grow in my current role",
    "adjacent": "move to a nearby role",
    "switch": "switch to a new field",
}


def ranking_inputs(profile: Profile, catalogue: Catalogue) -> list[str]:
    """Plain-language lines naming the profile answers the ranking used (empty if none)."""
    lines = []
    if (months := profile.preferences.timeframe_months) is not None:
        weeks = horizon_weeks(profile, params.EFFORT_HORIZON_WEEKS)
        lines.append(f"Timeframe {months} months: effort is counted over {weeks} weeks.")
    if (direction := profile.preferences.direction) is not None:
        fits = len(eligible_roles(profile, catalogue))
        lines.append(f"Direction: {DIRECTION_LABEL[direction]}. {fits} role(s) fit it.")
    return lines


def horizon_weeks(profile: Profile, default: int) -> int:
    """The person's own timeframe in weeks when they gave one, otherwise `default`.

    weeks = round(timeframe_months × 52/12). Used for the path budget and the effort horizon.
    """
    months = profile.preferences.timeframe_months
    return round(months * params.WEEKS_PER_MONTH) if months else default


def compute_factors(
    weights: dict[str, float],
    states: dict[str, SkillState],
    profile: Profile,
    role: Role,
    catalogue: Catalogue,
) -> Factors:
    total = sum(weights.values())
    coverage = sum(w * credit(states.get(k)) for k, w in weights.items()) / total
    evidenced = sum(
        w
        for k, w in weights.items()
        if (s := states.get(k)) and s.counted_events >= params.CONFIDENCE_MIN_EVENTS
    )
    interests = set(profile.interests)
    interest = len(interests & set(role.tags)) / len(interests) if interests else 0.0
    effort_capacity = profile.weekly_learning_hours * horizon_weeks(
        profile, params.EFFORT_HORIZON_WEEKS
    )
    effort = min(params.EFFORT_CAP, gap_hours(weights, states, catalogue) / effort_capacity)
    return Factors(
        coverage=coverage, confidence=evidenced / total, interest=interest, effort=effort
    )


def gap_list(weights: dict[str, float], states: dict[str, SkillState]) -> list[GapItem]:
    """Skills not yet demonstrated, largest weighted gap w·(1 − credit) first."""
    gaps = [(k, w, 1 - credit(states.get(k))) for k, w in weights.items()]
    ordered = sorted((g for g in gaps if g[2] > 0), key=lambda g: (-g[1] * g[2], g[0]))
    return [
        GapItem(
            skill_id=k,
            state=s.state if (s := states.get(k)) else "insufficient_evidence",
            weight=round(w, params.WEIGHT_DECIMALS),
        )
        for k, w, _ in ordered
    ]


def role_sources(
    role: Role, assumptions: CompanyAssumptions, snapshot: Snapshot | None
) -> list[SourceLink]:
    links = [
        SourceLink(label=f"O*NET 31.0 {b.code} {b.title} (CC BY 4.0)", url=b.url, kind="evidence")
        for b in role.based_on
    ]
    if snapshot:
        links.append(
            SourceLink(
                label=(
                    f"{snapshot.source}, release {snapshot.release_date}, period {snapshot.period}"
                ),
                url=snapshot.url,
                kind="evidence",
            )
        )
    links.append(
        SourceLink(
            label=f"Company assumptions v{assumptions.version} ({assumptions.updated_by})",
            url=ASSUMPTIONS_URL,
            kind="assumption",
        )
    )
    return links


def score_role(
    role: Role,
    scenario: Scenario,
    profile: Profile,
    states: dict[str, SkillState],
    catalogue: Catalogue,
    assumptions: CompanyAssumptions,
    snapshot: Snapshot | None = None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> tuple[RoleRecommendation, float]:
    """One role's recommendation (rank filled in by recommend) and its unclamped score."""
    skill_types = catalogue.skill_types
    skill_weights = scenario_weights(role, scenario, assumptions, skill_types).scenario
    factors = compute_factors(skill_weights, states, profile, role, catalogue)
    card = requirement_card(role, scenario, assumptions, skill_types, snapshot)
    rounded = Factors(
        **{k: round(v, params.SCORE_DECIMALS) for k, v in factors.model_dump().items()}
    )
    raw = weights.score(factors)
    hours = gap_hours(skill_weights, states, catalogue)
    recommendation = RoleRecommendation(
        role_id=role.id,
        rank=0,
        # Clamped for display; "+ 0.0" turns a rounded -0.0 into 0.0.
        score=max(params.SCORE_DISPLAY_FLOOR, round(raw, params.SCORE_DECIMALS)) + 0.0,
        factors=rounded,
        formula=weights.formula,
        gap=gap_list(skill_weights, states),
        requirement_card=card,
        sources=role_sources(role, assumptions, snapshot),
        title=role.title,
        sdg_targets=role.sdg_targets,
        score_note=params.SCORE_NOTE,
        outlook=card.outlook,
        fit=round(weights.fit(factors), params.FIT_DECIMALS),
        time_to_ready=TimeToReady(
            hours=round(hours, params.TIME_TO_READY_DECIMALS),
            weeks_at_current_budget=math.ceil(hours / profile.weekly_learning_hours),
        ),
    )
    return recommendation, raw


def recommend(
    profile: Profile,
    states: Sequence[SkillState],
    catalogue: Catalogue,
    assumptions: CompanyAssumptions,
    scenario: Scenario,
    snapshot: Snapshot | None = None,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> Recommendation:
    """Rank every internal role for one employee under one scenario (highest score first)."""
    by_skill = {s.skill_id: s for s in states}
    scored = [
        score_role(role, scenario, profile, by_skill, catalogue, assumptions, snapshot, weights)
        for role in catalogue.roles.values()
    ]
    ordered = sorted(scored, key=lambda pair: (-pair[1], pair[0].role_id))
    close = len(ordered) > 1 and ordered[0][1] - ordered[1][1] < params.CLOSE_MATCH_THRESHOLD
    # Direction only marks roles; the score and the rank stay the formula's.
    eligible = set(eligible_roles(profile, catalogue)) if profile.preferences.direction else None
    roles = [
        r.model_copy(
            update={
                "rank": rank,
                "close_match": close and rank <= 2,
                "matches_direction": None if eligible is None else r.role_id in eligible,
            }
        )
        for rank, (r, _) in enumerate(ordered, start=1)
    ]
    return Recommendation(
        user_id=profile.id,
        scenario=scenario,
        snapshot_id=snapshot.id if snapshot else None,
        assumptions_version=assumptions.version,
        roles=roles,
        profile_inputs=ranking_inputs(profile, catalogue),
    )


def changed_since(
    previous: Recommendation,
    current: Recommendation,
    because: str,
    previous_assumptions_version: int | None = None,
) -> ChangedSince:
    """Roles whose rank or score moved between two recommendations, each with a reason."""
    before = {r.role_id: r for r in previous.roles}
    changes = []
    for role in current.roles:
        old = before.get(role.role_id)
        if old is None or (old.rank == role.rank and old.score == role.score):
            continue
        changes.append(
            RankChange(
                role_id=role.role_id,
                from_rank=old.rank,
                to=role.rank,
                because=f"{because} (score {old.score:.2f} → {role.score:.2f})",
            )
        )
    return ChangedSince(
        assumptions_version=previous_assumptions_version,
        rank_changes=changes,
        outlook_changes=outlook_changes(previous, current, because),
    )


def outlook_changes(
    previous: Recommendation, current: Recommendation, because: str
) -> list[OutlookChange]:
    """Roles whose outlook label or AI-handled share moved (e.g. after an assumption approval)."""
    before = {r.role_id: r.outlook for r in previous.roles}
    changes = []
    for role in current.roles:
        old, new = before.get(role.role_id), role.outlook
        if old is None or new is None:
            continue
        if old.label == new.label and old.ai_handled_share == new.ai_handled_share:
            continue
        changes.append(
            OutlookChange(
                role_id=role.role_id,
                from_label=old.label,
                to_label=new.label,
                from_ai_handled_share=old.ai_handled_share,
                to_ai_handled_share=new.ai_handled_share,
                because=f"{because}; now {new.because}",
            )
        )
    return changes


def top_role_under_sensitivity(
    profile: Profile,
    states: Sequence[SkillState],
    catalogue: Catalogue,
    assumptions: CompanyAssumptions,
    scenario: Scenario,
    delta: float,
) -> dict[str, str]:
    """Top role when each formula weight is scaled by (1 ± delta), one at a time."""
    results = {"baseline": recommend(profile, states, catalogue, assumptions, scenario).roles[0]}
    for name in ("coverage", "confidence", "interest", "effort"):
        for sign, label in ((1, "+"), (-1, "-")):
            varied = replace(
                DEFAULT_WEIGHTS, **{name: getattr(DEFAULT_WEIGHTS, name) * (1 + sign * delta)}
            )
            rec = recommend(profile, states, catalogue, assumptions, scenario, weights=varied)
            results[f"{name}{label}"] = rec.roles[0]
    return {key: value.role_id for key, value in results.items()}
