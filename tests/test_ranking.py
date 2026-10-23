"""Unit tests for the role ranking (QART_NEXT_STEPS §5, §8): each component with small hand
calculations, the core-coverage cap, tie-breaking, the empty-profile path, the trend signal
feeding the ranking, and fairness (personal answers never change a score)."""

from dataclasses import replace

import pytest

from src.contract import Preferences, Profile
from src.engine.catalogue import LearnHours, SkillInfo, default_catalogue
from src.engine.ranking import (
    Answers,
    Signals,
    default_scoring,
    hours_between,
    rank_for_profile,
    rank_roles,
    score_role,
)
from src.engine.role_catalogue import (
    Family,
    RequiredLevel,
    RoleCatalogue,
    RoleSkill,
    RoleSource,
    TargetRole,
)

CFG = default_scoring()
EDU = ["secondary", "certification", "diploma", "bachelor", "master"]
SOURCE = RoleSource(dataset="O*NET OnLine", code="15-2051.00", title="t", url="u", verified=True)


def skill(sid: str, tracked: bool = True) -> SkillInfo:
    return SkillInfo(
        id=sid,
        name=sid.upper(),
        practised=False,
        learn_hours=LearnHours(to_basic=14, to_confident=30),
        trend_tracked=tracked,
    )


VOCAB = {k: skill(k) for k in ("a", "b", "c", "d")} | {"n": skill("n", tracked=False)}


def role(
    rid: str, family: str, skills: dict[str, int], industries: list[str] | None = None
) -> TargetRole:
    return TargetRole(
        id=rid,
        name=rid.title(),
        family=family,
        source=SOURCE,
        typical_industries=industries or [],
        min_education="bachelor",
        skills=[RoleSkill(id=k, weight=w) for k, w in skills.items()],  # type: ignore[arg-type]
        required_level=RequiredLevel(default=0.7),
    )


FAMILIES = [
    Family(id="home", name="Home", adjacent=["near"]),
    Family(id="near", name="Near", adjacent=["home"]),
    Family(id="far", name="Far", adjacent=[]),
]
ANSWERS = Answers("home", "adjacent", None, None, 3, 3.0)  # 3 h/week × 13 weeks = 39 h


def one(
    r: TargetRole,
    levels: dict[str, float],
    answers: Answers = ANSWERS,
    labels: dict[str, str] | None = None,
):  # type: ignore[no-untyped-def]
    cat = RoleCatalogue(roles=[r], families=FAMILIES)
    return score_role(
        r, levels, answers, Signals(labels or {}, data_as_of="2026-10-15"), cat, VOCAB, CFG, EDU
    )


def test_hours_between_is_linear_within_each_level_step() -> None:
    s = skill("x")  # 14 h to "use sometimes", 30 h more to "confident"
    assert hours_between(0, 0.7, s, 0.7) == pytest.approx(14)
    assert hours_between(0.3, 0.7, s, 0.7) == pytest.approx(8)
    assert hours_between(0.7, 1.0, s, 0.7) == pytest.approx(30)
    assert hours_between(0, 1.0, s, 0.7) == pytest.approx(44)
    assert hours_between(1.0, 0.7, s, 0.7) == 0


def test_components_match_hand_calculation() -> None:
    r = role("r", "near", {"a": 3, "b": 3, "c": 3, "n": 1})
    # a at the required level, b half way (0.35/0.7), c and n missing.
    got = one(r, {"a": 0.7, "b": 0.35}, labels={"a": "rising", "b": "cooling", "c": "stable"})
    assert got.components.skill == pytest.approx((3 * 1 + 3 * 0.5) / 10)
    assert got.components.momentum == pytest.approx((1 + 0 + 0.5) / 3)  # core, tracked only
    assert got.components.direction == 1.0  # nearby move to an adjacent family
    gap = 7 + 14 + 14  # b 0.35→0.7, c 0→0.7, n 0→0.7
    assert got.gap_hours == pytest.approx(gap)
    assert got.components.feasibility == 1.0  # 39 h available
    w = CFG.scenarios["moderate"].weights["adjacent"]
    expected = 100 * (w.skill * 0.45 + w.momentum * 0.5 + w.direction * 1 + w.feasibility * 1)
    assert got.score == round(expected)


def test_momentum_is_neutral_without_tracked_core_skills_and_says_so() -> None:
    r = role("r", "near", {"n": 3, "a": 1})
    got = one(r, {"n": 0.7}, labels={"a": "rising"})  # a is tracked but only nice-to-have
    assert got.components.momentum == CFG.momentum_neutral
    assert "No market trend data for this role's core skills." in got.reasons


def test_direction_table_and_industry_bonus() -> None:
    r_same, r_near, r_far = (role(x, x, {"a": 3}) for x in ("home", "near", "far"))
    for direction, expected in [("grow", (1.0, 0.4, 0.0)), ("switch", (0.2, 0.7, 1.0))]:
        answers = replace(ANSWERS, direction=direction)
        got = [one(r, {"a": 0.7}, answers).components.direction for r in (r_same, r_near, r_far)]
        assert got == pytest.approx(list(expected))
    with_industry = role("r", "far", {"a": 3}, industries=["Healthcare"])
    answers = replace(ANSWERS, industry="Healthcare")
    assert one(with_industry, {"a": 0.7}, answers).components.direction == pytest.approx(0.3)


def test_feasibility_uses_weekly_hours_times_timeframe_weeks() -> None:
    r = role("r", "near", {"a": 3, "b": 3})
    got = one(r, {}, replace(ANSWERS, weekly_hours=1.0))  # 28 h gap, 13 h available
    assert got.components.feasibility == pytest.approx(13 / 28)
    assert any("more than your 3-month plan at 1 h/week allows (13 h)" in x for x in got.reasons)
    longer = one(r, {}, replace(ANSWERS, weekly_hours=1.0, timeframe_months=12))  # 52 h
    assert longer.components.feasibility == 1.0


def test_core_coverage_cap_keeps_a_thin_match_in_stretch() -> None:
    r = role("r", "near", {"a": 3, "b": 3, "c": 3})
    got = one(r, {"a": 1.0}, labels={"a": "rising", "b": "rising", "c": "rising"})
    assert got.core_coverage < CFG.core_coverage_min
    assert got.capped and got.score == CFG.bands.good - 1 and got.band == "Stretch"
    assert any("less than half of its core skills" in f for f in got.flags)


def test_ties_break_on_momentum_then_name() -> None:
    roles = [
        role("b_role", "near", {"a": 3}),
        role("a_role", "near", {"b": 3}),
        role("c_role", "near", {"c": 3}),
    ]
    cat = RoleCatalogue(roles=roles, families=FAMILIES)
    levels = {"a": 0.7, "b": 0.7, "c": 0.7, "d": 0.7}
    labels = {"a": "stable", "b": "stable", "c": "stable"}
    order = [
        r.role_id for r in rank_roles(levels, ANSWERS, Signals(labels), cat, VOCAB, CFG, EDU).roles
    ]
    assert order == ["a_role", "b_role", "c_role"]  # same score and momentum: name A–Z
    ranked = rank_roles(levels, ANSWERS, Signals({**labels, "c": "rising"}), cat, VOCAB, CFG, EDU)
    assert ranked.roles[0].role_id == "c_role"


def test_fewer_than_three_skills_gives_starter_roles_not_a_ranking() -> None:
    cat = RoleCatalogue(roles=[role("r", "near", {"a": 3})], families=FAMILIES)
    result = rank_roles({"a": 0.7, "b": 0.3}, ANSWERS, Signals({}), cat, VOCAB, CFG, EDU)
    assert result.empty_profile and result.roles == [] and result.starter_roles == CFG.starter_roles
    assert result.message


def test_education_only_adds_a_flag() -> None:
    r = role("r", "near", {"a": 3})
    without = one(r, {"a": 0.7})
    lower = one(r, {"a": 0.7}, replace(ANSWERS, education_level="diploma"))
    assert lower.score == without.score and lower.components == without.components
    assert "Often asks for a bachelor's degree." in lower.flags and not without.flags


# --- With the real catalogue -----------------------------------------------------------------


def profile(**prefs: object) -> Profile:
    levels = {"python": "sometimes", "sql_basics": "confident", "data_visualisation": "sometimes"}
    return Profile(
        id="u_rank",
        display_name="Test (synthetic)",
        current_role_id="recon_associate",
        years_experience=3,
        weekly_learning_hours=4,
        team="t",
        preferences=Preferences.model_validate(
            {"current_job": "reconciliation_associate", "skill_levels": levels, **prefs}
        ),
    )


def snapshot(labels: dict[str, str]) -> dict[str, object]:
    ids = [s.id for s in default_catalogue().vocabulary.values() if s.trend_tracked]
    return {
        "source": "test",
        "data_as_of": "2026-10-15",
        "series": [{"id": i, "label": labels.get(i, "stable")} for i in ids],
    }


def test_a_new_trend_snapshot_visibly_changes_the_ranking() -> None:
    """Domain 1: 'the output visibly changes when the trend data changes'."""
    before = rank_for_profile(profile(), snapshot=snapshot({}))
    after = rank_for_profile(
        profile(), snapshot=snapshot({"python": "rising", "pytorch": "rising"})
    )
    score = lambda r, rid: next(x.score for x in r.roles if x.role_id == rid)  # noqa: E731
    assert score(after, "ml_engineer") > score(before, "ml_engineer")
    assert any(
        "Rising in tech hiring" in x
        for x in next(r for r in after.roles if r.role_id == "ml_engineer").reasons
    )
    cooled = rank_for_profile(profile(), snapshot=snapshot({"sql_basics": "cooling"}))
    assert score(cooled, "data_analyst") < score(before, "data_analyst")


def test_fairness_personal_answers_never_change_a_score() -> None:
    """Education, years of experience and free text never enter a component."""
    base = rank_for_profile(profile(), snapshot=snapshot({}))
    scores = {r.role_id: r.score for r in base.roles}
    for other in [
        profile(education="SPM / secondary school"),
        profile(education="Master's or higher"),
        profile(notes="I am 52 and a woman (synthetic)"),
        profile().model_copy(update={"years_experience": 25}),
    ]:
        assert {
            r.role_id: r.score for r in rank_for_profile(other, snapshot=snapshot({})).roles
        } == scores


# --- Scenarios (Domain 1 must-have 6) --------------------------------------------------------


def exposed_vocab(levels: dict[str, str]) -> dict[str, SkillInfo]:
    return {k: v.model_copy(update={"ai_exposure": levels.get(k, "low")}) for k, v in VOCAB.items()}


def test_every_role_is_scored_under_both_scenarios() -> None:
    r = role("r", "near", {"a": 3, "b": 3, "c": 3})
    got = one(r, {"a": 0.7, "b": 0.7, "c": 0.7})
    assert set(got.scenarios) == {"moderate", "fast"}
    assert got.scenario == "moderate" and got.score == got.scenarios["moderate"].score
    assert got.scenarios["moderate"].exposure_points == 0


def test_fast_scenario_takes_points_in_proportion_to_ai_exposure() -> None:
    r = role("r", "near", {"a": 3, "b": 3, "c": 3, "n": 1})
    cat = RoleCatalogue(roles=[r], families=FAMILIES)
    levels = {"a": 0.7, "b": 0.7, "c": 0.7}
    penalty = CFG.scenarios["fast"].exposure_penalty

    def fast(exposure: dict[str, str]):  # type: ignore[no-untyped-def]
        return score_role(
            r, levels, ANSWERS, Signals({}), cat, exposed_vocab(exposure), CFG, EDU, "fast"
        )

    low = fast({})
    high = fast({"a": "high", "b": "high", "c": "high"})
    mixed = fast({"a": "high", "b": "medium"})  # (1 + 0.5 + 0) / 3 of the core weight
    assert low.scenarios["fast"].exposure_points == 0 and low.exposed_core_skills == []
    assert high.scenarios["fast"].exposure_points == round(penalty)
    assert mixed.ai_exposure == pytest.approx(0.5) and mixed.exposed_core_skills == ["a"]
    assert mixed.scenarios["fast"].exposure_points == round(penalty * 0.5)
    assert "A is work AI can increasingly do on its own" in mixed.scenarios["fast"].note
    assert high.score == high.scenarios["fast"].score < low.score  # ranked by the chosen scenario


def test_the_chosen_scenario_orders_the_ranking() -> None:
    routine = role("routine", "near", {"a": 3, "b": 3})
    judgement = role("judgement", "near", {"c": 3, "d": 3})
    cat = RoleCatalogue(roles=[routine, judgement], families=FAMILIES)
    vocab = exposed_vocab({"a": "high", "b": "high"})
    levels = {"a": 0.7, "b": 0.7, "c": 0.7, "d": 0.5}  # slightly better at the routine role

    def order(scenario: str) -> list[str]:
        ranked = rank_roles(levels, ANSWERS, Signals({}), cat, vocab, CFG, EDU, scenario)
        return [x.role_id for x in ranked.roles]

    assert order("moderate") == ["routine", "judgement"]
    assert order("fast") == ["judgement", "routine"]
