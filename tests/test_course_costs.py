"""Course cost labels and the free/lower-cost preference in the path planner (item 4)."""

from src.engine import params
from src.engine.catalogue import default_case_index, default_catalogue
from src.engine.planner import (
    PlanInputs,
    Resource,
    cost_tier,
    greedy_select,
    plan_path,
    prefer_cheaper,
)
from src.engine.skills import derive_states


def course(course_id: str, cost: str, skills: dict[str, float], hours: float = 2.0) -> Resource:
    return Resource(
        id=course_id,
        ref=course_id,
        type="course",
        title=course_id,
        hours=hours,
        gains=skills,
        cost=cost,
    )


def test_cost_tiers_never_assume_free() -> None:
    assert cost_tier("free") == params.COST_TIER_FREE
    assert cost_tier("Free (optional paid certificate)") == params.COST_TIER_FREE
    assert cost_tier("low-cost (RM50)") == params.COST_TIER_LOW
    assert cost_tier("paid (Coursera)") == params.COST_TIER_PAID_OR_UNKNOWN
    assert cost_tier("no price shown (not stated as free)") == params.COST_TIER_PAID_OR_UNKNOWN


def test_cheaper_course_covering_the_same_gap_wins_even_if_longer() -> None:
    free_long = course("c_free", "free", {"controls_design": 0.3}, hours=4)
    paid_short = course("c_paid", "paid (Coursera)", {"controls_design": 0.3}, hours=1)
    broader_paid = course("c_paid_broad", "paid", {"controls_design": 0.3, "sql_basics": 0.3})
    kept = prefer_cheaper([free_long, paid_short, broader_paid])
    assert [c.id for c in kept] == ["c_free", "c_paid_broad"]


def test_equal_gap_cut_per_hour_ties_go_to_the_lower_cost_tier() -> None:
    inputs = PlanInputs(
        weights={"assistive": {"forecasting": 1.0}, "agentic": {"forecasting": 1.0}},
        remaining={"forecasting": 1.0},
    )
    paid = course("a_paid", "paid", {"forecasting": 0.3})
    free = course("z_free", "free", {"forecasting": 0.3})
    chosen = greedy_select(inputs, [paid, free], budget_hours=2.0)
    assert [c.id for c in chosen] == ["z_free"]


def test_coso_is_paid_and_verified_and_the_free_summary_is_preferred() -> None:
    cat = default_catalogue()
    assert cat.courses["course_16"].cost == "paid (Coursera)"
    assert cat.courses["course_16"].verified
    assert cat.courses["course_17"].cost == "free"
    states = derive_states("u_x", list(cat.skills), [], {})
    plan = plan_path(
        "u_x",
        "controls_assurance_analyst",
        10,
        states,
        cat,
        cat.assumptions_v1,
        default_case_index(),
        set(),
    )
    refs = [s.ref for s in plan.steps]
    assert "course_17" in refs and "course_16" not in refs
    assert all(step.cost for step in plan.steps)


def test_free_labels_have_a_recorded_cost_source() -> None:
    for course_item in default_catalogue().courses.values():
        assert course_item.cost_source, course_item.id
        if cost_tier(course_item.cost) == params.COST_TIER_FREE:
            assert "free" in course_item.cost_source.lower() or "no-cost" in course_item.cost_source


def test_every_non_practised_role_skill_has_a_verified_course() -> None:
    cat = default_catalogue()
    covered = {k for c in cat.courses.values() if c.verified for k in c.skills}
    for role in cat.roles.values():
        for skill in role.skills:
            if not cat.skills[skill.skill_id].practised:
                assert skill.skill_id in covered, (role.id, skill.skill_id)
