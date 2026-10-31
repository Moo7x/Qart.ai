"""Decision support around the fit score: what it means, how uncertain it is, what would change it.

All pure recomputation with the same engine; nothing here stores anything or calls a model.

* meters        – coverage (the fit), essential readiness, and profile completeness kept apart,
                  so one number never hides an unmet essential or a mostly unstated profile.
* fit_range     – low: unevidenced claims one level lower, unstated as none; high: claims as
                  stated, unstated at UNSTATED_HIGH_LEVEL. Assumption-based, not a statistical
                  interval (docs/PHASE2_PLAN.md §4 C2).
* band          – strong / good / fair / low from the fit (BAND_THRESHOLDS, an assumption).
* components    – each requirement's weight, claim, need, points and the evidence behind it.
* raise_options – the RAISE_SHOWN single-skill changes worth the most points, each re-scored.
* best_questions – the unstated skills whose answer would change this person's options most:
                  every candidate is answered both ways (QUESTION_ANSWERS) and the roles re-ranked.
* sensitivity   – each role's rank as the adoption intensity varies (SENSITIVITY_INTENSITIES).
* what_if       – a hypothetical profile change, compared exactly with today's results.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from src import params
from src.journey.store import SkillClaim, levels_of
from src.match.engine import Evidence, RoleMatch, Scenario, rank_roles, score_role
from src.pack import Pack

Levels = Mapping[str, int | None]
Claims = Mapping[str, SkillClaim]
RANGE_BASIS = "low: self-rated claims one level lower, unstated as none; high: unstated at working"
EVIDENCED_SOURCES = ("cv", "agent_check")


def is_evidenced(claim: SkillClaim | None) -> bool:
    """A claim backed by a CV sentence or an accepted progress check (still a claim)."""
    return claim is not None and claim.source in EVIDENCED_SOURCES and bool(claim.evidence)


def meters(match: RoleMatch) -> dict[str, Any]:
    total = sum(r.base_weight for r in match.requirements)
    stated = sum(r.base_weight for r in match.requirements if r.claimed is not None)
    unknown_essentials = [
        r.skill_name for r in match.requirements if r.essential and r.claimed is None
    ]
    below = [
        r.skill_name
        for r in match.requirements
        if r.essential and r.claimed is not None and r.claimed < r.required
    ]
    return {
        "coverage": match.fit,
        "essentials_ready": not below and not unknown_essentials,
        "essentials_below": below,  # stated and below the needed level
        "essentials_unstated": unknown_essentials,  # not stated: not a confirmed deficiency
        "completeness": round(100 * stated / total, 1) if total else 0.0,
        "stated": sum(r.claimed is not None for r in match.requirements),
        "requirements": len(match.requirements),
    }


def _range(
    pack: Pack,
    match: RoleMatch,
    levels: Levels,
    evidenced: set[str],
    scenario: Scenario,
    evidence: Evidence,
) -> dict[str, Any]:
    """Low: claims outside `evidenced` one level lower (minimum 0), unstated as none.
    High: claims as stated, unstated at UNSTATED_HIGH_LEVEL."""
    role = pack.destination_roles[match.role_id]
    low_levels = {
        skill: level if level is None or skill in evidenced else max(level - 1, 0)
        for skill, level in levels.items()
    }
    filled = dict(levels)
    for req in match.requirements:
        if req.claimed is None:
            filled[req.skill] = params.UNSTATED_HIGH_LEVEL
    low = score_role(pack, role, low_levels, scenario, evidence)
    high = score_role(pack, role, filled, scenario, evidence)
    return {"low": low.fit, "high": high.fit, "basis": RANGE_BASIS}


def evidenced_skills(claims: Claims) -> set[str]:
    return {skill for skill, claim in claims.items() if is_evidenced(claim)}


def fit_range(
    pack: Pack, match: RoleMatch, claims: Claims, scenario: Scenario, evidence: Evidence
) -> dict[str, Any]:
    """C2 range from the person's claims (docs/PHASE2_PLAN.md §4 C2)."""
    return _range(pack, match, levels_of(claims), evidenced_skills(claims), scenario, evidence)


def band(fit: float) -> str:
    for name, threshold in params.BAND_THRESHOLDS.items():
        if fit >= threshold:
            return name
    return params.BAND_BELOW


def components(match: RoleMatch, claims: Claims) -> list[dict[str, Any]]:
    """The fit, one row per requirement: fit = 100 × Σ w·min(c/r, 1) ÷ Σ w."""
    rows = []
    for req in match.requirements:
        claim = claims.get(req.skill)
        rows.append(
            {
                "skill": req.skill,
                "skill_name": req.skill_name,
                "weight": round(req.weight, 2),
                "claimed": req.claimed,
                "required": req.required,
                "points": round(req.contribution, 1),
                "evidenced": is_evidenced(claim),
                "evidence": claim.evidence if claim else "",
                "source": claim.source if claim and req.claimed is not None else "",
            }
        )
    return rows


def essentials_short(match: RoleMatch) -> list[str]:
    return [r.skill for r in match.requirements if r.essential and (r.claimed or 0) < r.required]


def raise_options(
    pack: Pack, match: RoleMatch, claims: Claims, scenario: Scenario, evidence: Evidence
) -> list[dict[str, Any]]:
    """The single-skill changes worth the most fit points, each computed by re-scoring.

    A skill below its need is tested at the required level: "study" if that level is within
    STUDY_MAX_LEVEL, "practice" above it. A skill at its level but unevidenced is a "check": its
    points are how much the bottom of the range rises once the claim is evidenced.
    """
    role = pack.destination_roles[match.role_id]
    levels = levels_of(claims)
    evidenced = evidenced_skills(claims)
    low_now = _range(pack, match, levels, evidenced, scenario, evidence)["low"]
    options: list[dict[str, Any]] = []
    for req in match.requirements:
        now = req.claimed or 0
        if now < req.required:
            after = score_role(pack, role, {**levels, req.skill: req.required}, scenario, evidence)
            points = after.fit - match.fit
            via = "study" if req.required <= params.STUDY_MAX_LEVEL else "practice"
            target = req.required
        elif req.skill not in evidenced:
            checked = evidenced | {req.skill}
            points = _range(pack, match, levels, checked, scenario, evidence)["low"] - low_now
            via, target = "check", now
        else:
            continue
        if points > 0:
            options.append(
                {
                    "skill": req.skill,
                    "skill_name": req.skill_name,
                    "from_level": req.claimed,
                    "to_level": target,
                    "points": round(points, 1),
                    "via": via,
                }
            )
    options.sort(key=lambda o: -float(o["points"]))
    return options[: params.RAISE_SHOWN]


@dataclass(frozen=True)
class Question:
    skill: str
    skill_name: str
    value: float  # declared ranking value, see best_questions
    top_role_changes: bool
    essential_for: list[str]  # role titles where this is an essential requirement
    swing: float  # largest fit difference between the two answers, among affected roles
    effect: str  # plain sentence of what each answer would do


def best_questions(
    pack: Pack,
    levels: Levels,
    scenario: Scenario,
    evidence: Evidence,
    interests: set[str] | None,
    destination: str | None,
) -> list[Question]:
    """Rank unstated skills by how much their answer changes the person's options.

    value = QUESTION_WEIGHT_GOAL_ESSENTIAL if it is an essential of the chosen (else top) role
          + QUESTION_WEIGHT_TOP_CHANGE if the best-fitting role differs between the answers
          + the largest fit swing on any role. Declared ordering, not a model.
    """
    base = rank_roles(pack, levels, scenario, evidence, interests)
    focus = destination or base[0].role_id
    candidates = {
        r.skill
        for role in pack.destination_roles.values()
        for r in role.requires
        if levels.get(r.skill) is None
    }
    out = []
    low_answer, high_answer = params.QUESTION_ANSWERS
    for skill in candidates:
        low = rank_roles(pack, {**levels, skill: low_answer}, scenario, evidence, interests)
        high = rank_roles(pack, {**levels, skill: high_answer}, scenario, evidence, interests)
        low_fit = {m.role_id: m.fit for m in low}
        high_fit = {m.role_id: m.fit for m in high}
        swing_role = max(high_fit, key=lambda r: high_fit[r] - low_fit[r])
        swing = round(high_fit[swing_role] - low_fit[swing_role], 1)
        essential_for = [
            role.title
            for role in pack.destination_roles.values()
            if any(r.skill == skill and r.essential for r in role.requires)
        ]
        focus_essential = any(
            r.skill == skill and r.essential for r in pack.destination_roles[focus].requires
        )
        changes = low[0].role_id != high[0].role_id
        value = (
            params.QUESTION_WEIGHT_GOAL_ESSENTIAL * focus_essential
            + params.QUESTION_WEIGHT_TOP_CHANGE * changes
            + swing
        )
        name = pack.skills[skill].name
        title = pack.destination_roles[swing_role].title
        low_word, high_word = (params.PROFICIENCY_LABELS[a] for a in params.QUESTION_ANSWERS)
        if changes:
            effect = (
                f"At '{low_word}' your best fit is {low[0].title}; at '{high_word}' it becomes "
                f"{high[0].title}."
            )
        else:
            effect = (
                f"Moves {title} by up to {swing:.1f} fit points between '{low_word}' and "
                f"'{high_word}'."
            )
        if focus_essential:
            effect += f" It is essential for {pack.destination_roles[focus].title}."
        out.append(Question(skill, name, value, changes, essential_for, swing, effect))
    out.sort(key=lambda q: (-q.value, q.skill))
    return out[: params.QUESTIONS_SHOWN]


def sensitivity(
    pack: Pack,
    levels: Levels,
    scenario: Scenario,
    evidence: Evidence,
    interests: set[str] | None,
) -> dict[str, Any]:
    """Each role's rank under every declared adoption intensity."""
    ranks: dict[str, list[int]] = {}
    for intensity in params.SENSITIVITY_INTENSITIES:
        ranked = rank_roles(pack, levels, scenario, evidence, interests, intensity)
        for i, match in enumerate(ranked, 1):
            ranks.setdefault(match.role_id, []).append(i)
    return {
        "intensities": list(params.SENSITIVITY_INTENSITIES),
        "roles": [
            {
                "role_id": role_id,
                "title": pack.destination_roles[role_id].title,
                "ranks": r,
                "stable": min(r) == max(r),
            }
            for role_id, r in ranks.items()
        ],
    }


def what_if(
    pack: Pack,
    levels: Levels,
    changes: Mapping[str, int | None],
    scenario: Scenario,
    evidence: Evidence,
    interests: set[str] | None,
) -> list[dict[str, Any]]:
    """Today's ranking against a hypothetical one; the saved profile is not touched."""
    now = rank_roles(pack, levels, scenario, evidence, interests)
    then = rank_roles(pack, {**levels, **changes}, scenario, evidence, interests)
    before = {m.role_id: (i, m.fit) for i, m in enumerate(now, 1)}
    return [
        {
            "role_id": m.role_id,
            "title": m.title,
            "rank_now": before[m.role_id][0],
            "rank_then": i,
            "fit_now": before[m.role_id][1],
            "fit_then": m.fit,
        }
        for i, m in enumerate(then, 1)
    ]
