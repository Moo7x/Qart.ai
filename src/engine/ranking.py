"""Role ranking (QART_NEXT_STEPS §5): one pure, deterministic function, `rank_roles`.

For each role in catalogue/target_roles.json, four components in 0–1:
  skill        Σ(weight × min(level / required, 1)) / Σ(weight) over the role's skills
  momentum     mean over the role's core skills that the radar tracks with a usable label:
               rising 1, stable 0.5, cooling 0 (no tracked core skill → neutral 0.5)
  direction    fit of the person's direction to same / adjacent / far family, + industry bonus
  feasibility  min(1, available hours / hours to close the gap); 1 when there is no gap
score = round(100 × Σ weight × component), with the weights of the person's direction.
Guards: a person covering under half of a role's core weight is capped at the top of
"Stretch"; fewer than `min_skills_for_ranking` skills gives starter roles, not a ranking.
Ties: score, then momentum, then name. Reasons and flags are templates built from the same
numbers, so the explanation can never disagree with the score. Age, citizenship, education and
free text never enter a component (education only adds a flag).
No I/O, no network, no randomness: `rank_for_profile` loads the inputs and calls `rank_roles`.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel

from src.contract import Profile, SkillState
from src.engine.catalogue import CATALOGUE_DIR, SkillInfo, default_catalogue
from src.engine.questionnaire import Questionnaire, default_questionnaire, held_skills
from src.engine.role_catalogue import (
    CORE_WEIGHT,
    RoleCatalogue,
    TargetRole,
    default_role_catalogue,
)

SCORING_PATH = CATALOGUE_DIR / "scoring.json"
BANDS = ("Strong match", "Good match", "Stretch")
Relation = str  # "same" | "adjacent" | "far"


class Weights(BaseModel):
    skill: float
    momentum: float
    direction: float
    feasibility: float


class Bands(BaseModel):
    strong: int
    good: int


class ScoringConfig(BaseModel):
    weights: dict[str, Weights]
    default_direction: str
    direction_fit: dict[str, dict[str, float]]
    industry_bonus: float
    momentum_values: dict[str, float]
    momentum_neutral: float
    bands: Bands
    core_coverage_min: float
    min_skills_for_ranking: int
    timeframe_weeks: dict[str, int]
    default_timeframe_months: int
    basic_level: (
        float  # the "use sometimes" level, where learn_hours switch from basic to confident
    )
    starter_roles: list[str]


@lru_cache(maxsize=1)
def default_scoring(path: Path = SCORING_PATH) -> ScoringConfig:
    return ScoringConfig.model_validate_json(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Answers:
    """The questionnaire answers the ranking reads (nothing else about the person)."""

    family: str | None  # current job's role family; None for "recent graduate or student"
    direction: str | None
    industry: str | None
    education_level: str | None
    timeframe_months: int | None
    weekly_hours: float


@dataclass(frozen=True)
class Signals:
    """Radar labels by skill id, with the snapshot date (provenance for reasons)."""

    labels: Mapping[str, str]
    source: str = ""
    data_as_of: str = ""


@dataclass(frozen=True)
class Components:
    skill: float
    momentum: float
    direction: float
    feasibility: float


@dataclass(frozen=True)
class MatchedSkill:
    skill_id: str
    name: str
    user_level: float
    required_level: float
    is_core: bool
    has_it: bool


@dataclass(frozen=True)
class RankedRole:
    role_id: str
    name: str
    family: str
    score: int
    band: str
    components: Components
    weights_used: Weights
    relation: Relation
    matched_skills: list[MatchedSkill]
    core_coverage: float
    capped: bool
    gap_hours: float
    available_hours: float
    momentum_skills: dict[str, str]  # core skill id -> radar label used
    reasons: list[str]
    flags: list[str]
    source_code: str
    source_url: str | None


@dataclass(frozen=True)
class Ranking:
    roles: list[RankedRole]
    empty_profile: bool
    starter_roles: list[str] = field(default_factory=list)
    message: str | None = None
    signals_source: str = ""
    signals_data_as_of: str = ""


def hours_between(start: float, end: float, skill: SkillInfo, basic: float) -> float:
    """Hours to go from `start` to `end`, linear within each learn_hours step.

    0 → basic ("use sometimes") costs to_basic; basic → 1.0 ("confident") costs to_confident.
    """
    if end <= start or skill.learn_hours is None:
        return 0.0
    lh = skill.learn_hours
    low = max(0.0, min(end, basic) - min(start, basic)) / basic * lh.to_basic
    high = max(0.0, max(end, basic) - max(start, basic)) / (1 - basic) * lh.to_confident
    return low + high


def relation(person_family: str | None, role: TargetRole, catalogue: RoleCatalogue) -> Relation:
    if person_family is None:
        return "far"
    if person_family == role.family:
        return "same"
    return "adjacent" if catalogue.adjacent(person_family, role.family) else "far"


def _band(score: int, cfg: ScoringConfig) -> str:
    if score >= cfg.bands.strong:
        return BANDS[0]
    return BANDS[1] if score >= cfg.bands.good else BANDS[2]


def _names(ids: list[str], vocabulary: Mapping[str, SkillInfo]) -> str:
    names = [vocabulary[i].name for i in ids]
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def score_role(
    role: TargetRole,
    levels: Mapping[str, float],
    answers: Answers,
    signals: Signals,
    catalogue: RoleCatalogue,
    vocabulary: Mapping[str, SkillInfo],
    cfg: ScoringConfig,
    education_order: list[str],
) -> RankedRole:
    direction = answers.direction or cfg.default_direction
    weights = cfg.weights[direction]
    matched, gap_hours = [], 0.0
    weighted = total = core_weighted = core_total = 0.0
    for rs in role.skills:
        required = role.required(rs)
        level = levels.get(rs.id, 0.0)
        ratio = min(level / required, 1.0)
        weighted += rs.weight * ratio
        total += rs.weight
        is_core = rs.weight == CORE_WEIGHT
        if is_core:
            core_weighted += rs.weight * ratio
            core_total += rs.weight
        gap_hours += hours_between(level, required, vocabulary[rs.id], cfg.basic_level)
        matched.append(
            MatchedSkill(rs.id, vocabulary[rs.id].name, level, required, is_core, level >= required)
        )
    skill = weighted / total
    core_coverage = core_weighted / core_total

    tracked = {
        s.id: signals.labels[s.id]
        for s in role.core_skills
        if vocabulary[s.id].trend_tracked and signals.labels.get(s.id) in cfg.momentum_values
    }
    momentum = (
        sum(cfg.momentum_values[label] for label in tracked.values()) / len(tracked)
        if tracked
        else cfg.momentum_neutral
    )

    rel = relation(answers.family, role, catalogue)
    industry_match = answers.industry is not None and answers.industry in role.typical_industries
    fit = cfg.direction_fit[direction][rel] + (cfg.industry_bonus if industry_match else 0.0)
    direction_fit = min(1.0, fit)

    months = answers.timeframe_months or cfg.default_timeframe_months
    available = answers.weekly_hours * cfg.timeframe_weeks[str(months)]
    feasibility = 1.0 if gap_hours == 0 else min(1.0, available / gap_hours)

    components = Components(skill, momentum, direction_fit, feasibility)
    raw = round(
        100
        * (
            weights.skill * skill
            + weights.momentum * momentum
            + weights.direction * direction_fit
            + weights.feasibility * feasibility
        )
    )
    capped = core_coverage < cfg.core_coverage_min and raw >= cfg.bands.good
    score = cfg.bands.good - 1 if capped else raw

    reasons = _reasons(
        matched, tracked, signals, rel, catalogue, answers, gap_hours, available, months, vocabulary
    )
    flags = _flags(role, answers, education_order, capped)
    return RankedRole(
        role_id=role.id,
        name=role.name,
        family=role.family,
        score=score,
        band=_band(score, cfg),
        components=components,
        weights_used=weights,
        relation=rel,
        matched_skills=matched,
        core_coverage=core_coverage,
        capped=capped,
        gap_hours=round(gap_hours, 1),
        available_hours=round(available, 1),
        momentum_skills=tracked,
        reasons=reasons,
        flags=flags,
        source_code=role.source.code,
        source_url=role.source.url,
    )


def _reasons(
    matched: list[MatchedSkill],
    tracked: Mapping[str, str],
    signals: Signals,
    rel: Relation,
    catalogue: RoleCatalogue,
    answers: Answers,
    gap_hours: float,
    available: float,
    months: int,
    vocabulary: Mapping[str, SkillInfo],
) -> list[str]:
    """Up to three template sentences, each built only from the computed numbers."""
    core = [m for m in matched if m.is_core]
    have = [m.skill_id for m in core if m.has_it]
    if have:
        reasons = [
            f"You already have {len(have)} of {len(core)} core skills ({_names(have, vocabulary)})."
        ]
    else:
        reasons = [f"You don't have any of its {len(core)} core skills yet."]
    rising = [k for k, v in tracked.items() if v == "rising"]
    cooling = [k for k, v in tracked.items() if v == "cooling"]
    dated = f"in tech hiring (data to {signals.data_as_of})"
    if rising:
        verb = "is" if len(rising) == 1 else "are"
        reasons.append(f"{_names(rising, vocabulary)} {verb} Rising {dated}.")
    elif cooling:
        verb = "is" if len(cooling) == 1 else "are"
        reasons.append(f"{_names(cooling, vocabulary)} {verb} Cooling {dated}.")
    elif not tracked:
        reasons.append("No market trend data for this role's core skills.")
    else:
        reasons.append(f"Its core skills are Stable {dated}.")
    hours, plan = round(gap_hours), f"{months}-month plan at {answers.weekly_hours:g} h/week"
    if gap_hours == 0:
        reasons.append("You already meet the level it asks for in every skill.")
    elif available >= gap_hours:
        reasons.append(f"Closing the gap needs ~{hours} h, which fits your {plan}.")
    else:
        reasons.append(
            f"Closing the gap needs ~{hours} h, more than your {plan} allows "
            f"({round(available)} h). Consider a longer timeframe."
        )
    return reasons


def direction_sentence(rel: Relation, person_family: str | None, catalogue: RoleCatalogue) -> str:
    """Plain words for the direction component (shown in the calculation panel)."""
    name = next((f.name for f in catalogue.families if f.id == person_family), None)
    if rel == "same":
        return f"Same field as your current work ({name})."
    if rel == "adjacent":
        return f"A nearby move from {name}: it uses what you already know."
    return "A new field for you."


def _flags(
    role: TargetRole, answers: Answers, education_order: list[str], capped: bool
) -> list[str]:
    flags = []
    if answers.education_level in education_order and education_order.index(
        answers.education_level
    ) < education_order.index(role.min_education):
        wording = {
            "bachelor": "a bachelor's degree",
            "master": "a master's degree",
            "diploma": "a diploma",
        }
        flags.append(f"Often asks for {wording.get(role.min_education, role.min_education)}.")
    if capped:
        flags.append("You have less than half of its core skills, so it is shown as a stretch.")
    if role.source.code == "TODO":
        flags.append("Its public occupation code is not confirmed yet.")
    return flags


def rank_roles(
    levels: Mapping[str, float],
    answers: Answers,
    signals: Signals,
    catalogue: RoleCatalogue,
    vocabulary: Mapping[str, SkillInfo],
    cfg: ScoringConfig,
    education_order: list[str],
) -> Ranking:
    """Rank every catalogue role for one person. Pure and deterministic."""
    held = {k: v for k, v in levels.items() if v > 0}
    if len(held) < cfg.min_skills_for_ranking:
        return Ranking(
            roles=[],
            empty_profile=True,
            starter_roles=list(cfg.starter_roles),
            message="Add a few skills or tasks to get a personalised ranking.",
            signals_source=signals.source,
            signals_data_as_of=signals.data_as_of,
        )
    ranked = [
        score_role(r, held, answers, signals, catalogue, vocabulary, cfg, education_order)
        for r in catalogue.roles
    ]
    ranked.sort(key=lambda r: (-r.score, -r.components.momentum, r.name))
    return Ranking(
        roles=ranked,
        empty_profile=False,
        signals_source=signals.source,
        signals_data_as_of=signals.data_as_of,
    )


# --- Loading the inputs (I/O lives here, outside the pure function) --------------------------


def answers_for(profile: Profile, q: Questionnaire) -> Answers:
    prefs = profile.preferences
    job = next((r for r in q.current_roles if r.id == prefs.current_job), None)
    education = next((e.level for e in q.education if e.label == prefs.education), None)
    return Answers(
        family=job.family if job else None,
        direction=prefs.direction,
        industry=prefs.industry,
        education_level=education,
        timeframe_months=prefs.timeframe_months,
        weekly_hours=profile.weekly_learning_hours,
    )


def signals_from_snapshot(snapshot: Mapping[str, object] | None) -> Signals:
    if not snapshot:
        return Signals(labels={})
    series = snapshot.get("series", [])
    labels = {s["id"]: s["label"] for s in series} if isinstance(series, list) else {}
    return Signals(
        labels=labels,
        source=str(snapshot.get("source", "")),
        data_as_of=str(snapshot.get("data_as_of", "")),
    )


def rank_for_profile(
    profile: Profile,
    states: list[SkillState] | None = None,
    snapshot: Mapping[str, object] | None = None,
) -> Ranking:
    """Convenience wrapper: questionnaire + evidence → levels, default catalogue and config."""
    from src.api_signals import read_snapshot  # noqa: PLC0415 (avoids an import cycle)
    from src.signals.pipeline import SKILL_SIGNALS  # noqa: PLC0415

    q = default_questionnaire()
    held = held_skills(profile, states or [], q)
    if snapshot is None:
        try:
            snapshot = read_snapshot(SKILL_SIGNALS)
        except Exception:  # no snapshot yet: neutral momentum, reasons say so
            snapshot = None
    return rank_roles(
        {k: h.value for k, h in held.items()},
        answers_for(profile, q),
        signals_from_snapshot(snapshot),
        default_role_catalogue(),
        default_catalogue().vocabulary,
        default_scoring(),
        q.education_order,
    )
