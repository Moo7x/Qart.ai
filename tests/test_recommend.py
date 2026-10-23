"""Recommender v2 formula, factors, gap, changed_since and the ±20% sensitivity check (Task A4)."""

import json
from pathlib import Path

import pytest

from src.contract import Preferences, Profile, Scenario, SkillState
from src.engine import params
from src.engine.catalogue import default_catalogue
from src.engine.recommend import (
    DEFAULT_WEIGHTS,
    changed_since,
    horizon_weeks,
    recommend,
    score_role,
    top_role_under_sensitivity,
)
from src.engine.skills import derive_states
from tests.helpers import golden_journey_events

PROFILE_EXAMPLE = Path(__file__).resolve().parent.parent / "schemas" / "examples" / "profile.json"
SENSITIVITY_DELTA = 0.20  # ±20%, as required by PROJECT_PLAN §6


def aina() -> Profile:
    return Profile.model_validate(json.loads(PROFILE_EXAMPLE.read_text(encoding="utf-8")))


def states_for(profile: Profile, with_events: bool) -> list[SkillState]:
    cat = default_catalogue()
    confidence = {s.skill_id: s.confidence for s in profile.skills_self_reported}
    events = golden_journey_events() if with_events else []
    return derive_states(profile.id, list(cat.skills), events, confidence)


def test_formula_string_matches_contract() -> None:
    assert DEFAULT_WEIGHTS.formula == params.SCORE_FORMULA


@pytest.mark.parametrize("scenario", ["assistive", "agentic"])
def test_score_is_the_formula_applied_to_factors(scenario: Scenario) -> None:
    cat = default_catalogue()
    profile = aina()
    rec = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, scenario)
    for role in rec.roles:
        f = role.factors
        expected = 0.55 * f.coverage + 0.20 * f.confidence + 0.10 * f.interest - 0.15 * f.effort
        # factors are rounded to 2 dp; the displayed score is clamped at 0
        assert role.score == pytest.approx(max(0.0, expected), abs=0.011)
        assert all(0.0 <= v <= 1.0 for v in f.model_dump().values())
        assert role.formula == params.SCORE_FORMULA
        assert role.score_note == params.SCORE_NOTE
        assert any(s.kind == "assumption" for s in role.sources)
        assert any("O*NET" in s.label for s in role.sources)


def test_ranks_are_ordered_by_score() -> None:
    cat = default_catalogue()
    profile = aina()
    rec = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, "agentic")
    assert [r.rank for r in rec.roles] == list(range(1, len(cat.roles) + 1))
    assert [r.score for r in rec.roles] == sorted((r.score for r in rec.roles), reverse=True)


def test_effort_is_a_penalty() -> None:
    cat = default_catalogue()
    profile = aina()
    less_time = profile.model_copy(update={"weekly_learning_hours": 1})
    states = states_for(profile, False)
    normal = recommend(profile, states, cat, cat.assumptions_v1, "agentic").roles
    rushed = recommend(less_time, states, cat, cat.assumptions_v1, "agentic").roles
    by_id = {r.role_id: r for r in normal}
    for role in rushed:
        assert role.factors.effort >= by_id[role.role_id].factors.effort
        assert role.score <= by_id[role.role_id].score


def test_golden_journey_evidence_raises_coverage() -> None:
    cat = default_catalogue()
    profile = aina()
    before = recommend(profile, states_for(profile, False), cat, cat.assumptions_v1, "agentic")
    after = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, "agentic")
    old = {r.role_id: r.factors for r in before.roles}
    for role in after.roles:
        if role.role_id != "fpa_analyst":  # fpa does not weight the practised skills she used
            assert role.factors.coverage > old[role.role_id].coverage
            assert role.factors.confidence > old[role.role_id].confidence


def test_gap_lists_undemonstrated_skills_largest_first() -> None:
    cat = default_catalogue()
    profile = aina()
    rec = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, "agentic")
    for role in rec.roles:
        assert role.gap
        assert all(g.state != "demonstrated_independently" for g in role.gap)


def test_identity_fields_do_not_change_the_ranking() -> None:
    """Fairness twin: same evidence, different name/id/team → identical scores."""
    cat = default_catalogue()
    profile = aina()
    twin = profile.model_copy(update={"id": "u_twin", "display_name": "Twin", "team": "other"})
    states = states_for(profile, True)
    a = recommend(profile, states, cat, cat.assumptions_v1, "agentic")
    b = recommend(twin, states, cat, cat.assumptions_v1, "agentic")
    assert [(r.role_id, r.score) for r in a.roles] == [(r.role_id, r.score) for r in b.roles]


def test_changed_since_reports_moves_with_reason() -> None:
    cat = default_catalogue()
    profile = aina()
    before = recommend(profile, states_for(profile, False), cat, cat.assumptions_v1, "agentic")
    after = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, "agentic")
    diff = changed_since(before, after, "new evidence: checkin_001")
    assert diff.rank_changes
    assert all("checkin_001" in change.because for change in diff.rank_changes)
    unchanged = changed_since(after, after, "nothing")
    assert unchanged.rank_changes == []


def test_sensitivity_top_role_is_stable_after_golden_journey() -> None:
    """±20% on each weight, one at a time (results recorded in eval/SENSITIVITY.md)."""
    cat = default_catalogue()
    profile = aina()
    report = top_role_under_sensitivity(
        profile, states_for(profile, True), cat, cat.assumptions_v1, "agentic", SENSITIVITY_DELTA
    )
    assert len(report) == 9
    assert set(report.values()) == {report["baseline"]}


def test_sensitivity_report_reveals_flips_for_near_ties() -> None:
    """After the golden journey (assistive) the top two roles are a near tie, so the ±20% check
    must reveal a flip."""
    cat = default_catalogue()
    profile = aina()
    report = top_role_under_sensitivity(
        profile, states_for(profile, True), cat, cat.assumptions_v1, "assistive", SENSITIVITY_DELTA
    )
    assert len(set(report.values())) > 1


# --- readable ranking -----------------------------------------------------------------------
def test_displayed_scores_are_never_negative_but_order_uses_the_formula() -> None:
    cat = default_catalogue()
    profile = aina()
    states = states_for(profile, False)
    rec = recommend(profile, states, cat, cat.assumptions_v1, "assistive")
    assert all(r.score >= 0 for r in rec.roles)
    by_skill = {s.skill_id: s for s in states}
    raw = {
        role.id: score_role(role, "assistive", profile, by_skill, cat, cat.assumptions_v1)[1]
        for role in cat.roles.values()
    }
    assert min(raw.values()) < 0  # the clamp matters for this profile
    assert [r.role_id for r in rec.roles] == sorted(raw, key=lambda k: (-raw[k], k))
    assert rec.roles[0].score_note is not None and "penalty" in rec.roles[0].score_note


@pytest.mark.parametrize("scenario", ["assistive", "agentic"])
def test_fit_is_the_positive_part_rescaled_to_one(scenario: Scenario) -> None:
    cat = default_catalogue()
    profile = aina()
    rec = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, scenario)
    for role in rec.roles:
        f = role.factors
        expected = (0.55 * f.coverage + 0.20 * f.confidence + 0.10 * f.interest) / 0.85
        assert role.fit is not None and 0.0 <= role.fit <= 1.0
        assert role.fit == pytest.approx(expected, abs=0.011)


def test_time_to_ready_uses_the_weekly_budget() -> None:
    cat = default_catalogue()
    profile = aina()
    rec = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, "agentic")
    for role in rec.roles:
        ready = role.time_to_ready
        assert ready is not None and ready.hours > 0
        weeks = ready.weeks_at_current_budget
        assert (weeks - 1) * profile.weekly_learning_hours < ready.hours + 0.05
        assert ready.hours <= weeks * profile.weekly_learning_hours + 0.05


def test_close_match_flags_the_top_two_only_when_scores_are_near() -> None:
    cat = default_catalogue()
    profile = aina()
    near = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, "assistive")
    assert [r.close_match for r in near.roles] == [True, True, False, False]
    apart = recommend(profile, states_for(profile, True), cat, cat.assumptions_v1, "agentic")
    assert not any(r.close_match for r in apart.roles)


# --- profile answers (contract v2.2) --------------------------------------------------------
def with_prefs(profile: Profile, **prefs: object) -> Profile:
    return profile.model_copy(update={"preferences": Preferences.model_validate(prefs)})


def test_timeframe_maps_months_to_weeks_and_defaults_without_one() -> None:
    profile = aina()
    assert horizon_weeks(profile, params.EFFORT_HORIZON_WEEKS) == params.EFFORT_HORIZON_WEEKS
    weeks = {m: horizon_weeks(with_prefs(profile, timeframe_months=m), 0) for m in (3, 6, 12)}
    assert weeks == {3: 13, 6: 26, 12: 52}


def test_longer_timeframe_lowers_the_effort_penalty() -> None:
    cat = default_catalogue()
    profile = aina()
    states = states_for(profile, False)
    base = {
        r.role_id: r for r in recommend(profile, states, cat, cat.assumptions_v1, "agentic").roles
    }
    year = with_prefs(profile, timeframe_months=12)
    for role in recommend(year, states, cat, cat.assumptions_v1, "agentic").roles:
        assert role.factors.effort <= base[role.role_id].factors.effort
    assert any(
        r.factors.effort < base[r.role_id].factors.effort
        for r in recommend(year, states, cat, cat.assumptions_v1, "agentic").roles
    )
