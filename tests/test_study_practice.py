"""Study versus practice (B4): study gives level 2 at most; levels above it come from practice."""

import pytest

from src import params
from src.journey.store import claims_from_levels
from src.match.engine import Evidence, score_role
from src.pack import Course, load_pack
from src.pathway.planner import (
    WeekRange,
    level_after_study,
    pathway_out,
    plan_pathway,
    study_level,
)

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")
ROLES = list(load_pack().destination_roles)


def course(minutes: int, hands_on: bool = False) -> Course:
    return Course(
        id=f"fixture_{minutes}_{hands_on}",
        title="Fixture course",
        provider="test",
        url="https://example.com",
        minutes=minutes,
        level="beginner",
        covers=["erp"],
        hands_on=hands_on,
    )


def test_study_never_takes_a_skill_above_the_study_maximum() -> None:
    long_hands_on = [course(60 * 100, hands_on=True)]
    assert level_after_study(long_hands_on, "erp", 0, 3) == params.STUDY_MAX_LEVEL == 2
    assert level_after_study(long_hands_on, "erp", 0, 1) == 1  # never above the need either


def test_twenty_hours_without_hands_on_material_stays_at_level_1() -> None:
    assert study_level(params.LEVEL2_MIN_HOURS, hands_on=False) == 1
    assert level_after_study([course(60 * 20)], "erp", 0, 2) == 1
    assert level_after_study([course(60 * 20, hands_on=True)], "erp", 0, 2) == 2
    assert level_after_study([course(30)], "erp", 0, 2) == 0  # under LEVEL1_MIN_HOURS


def _plan(role_id: str, levels: dict[str, int | None]):  # type: ignore[no-untyped-def]
    pack = load_pack()
    match = score_role(pack, pack.destination_roles[role_id], levels, "moderate", EVIDENCE)
    return match, plan_pathway(pack, match, claims_from_levels(levels), 6, "moderate", EVIDENCE)


@pytest.mark.parametrize("role_id", ROLES)
def test_practice_steps_only_for_levels_above_2_and_totals_are_consistent(role_id: str) -> None:
    match, path = _plan(role_id, {})
    for p in path.practice_steps:
        assert p.target_level > params.STUDY_MAX_LEVEL and p.kind == "practice"
        req = next(r for r in match.requirements if r.skill == p.skill)
        assert p.target_level <= req.required
        assert 0 < p.time.low <= p.time.high
    expected = {r.skill for r in match.requirements if r.required > params.STUDY_MAX_LEVEL}
    assert {p.skill for p in path.practice_steps} == expected
    assert pathway_out(path, load_pack(), "moderate").study_hours == path.total_hours
    assert path.total_hours == pytest.approx(sum(s.hours for s in path.steps))
    assert path.practice_weeks == WeekRange(
        sum(int(p.time.low or 0) for p in path.practice_steps),
        sum(int(p.time.high or 0) for p in path.practice_steps),
    )
    for fit in (path.fit_after_study, path.fit_after_practice):
        assert fit.low <= fit.high and fit.kind == "estimate"
    assert path.fit_after_practice.high >= path.fit_after_study.high
    assert all(v <= params.STUDY_MAX_LEVEL for v in path.study_levels.values())


def test_course_steps_carry_the_c3_fields() -> None:
    _, path = _plan("o2c_reporting_analyst", {})
    first, *rest = path.steps
    assert first.kind == "course" and first.id == first.course.id and first.unlock is None
    assert first.time.unit == "hours" and first.time.basis == first.course.time_basis
    assert all(s.unlock == "previous_step" for s in rest)


def test_a_skill_already_at_level_2_goes_straight_to_practice() -> None:
    pack = load_pack()
    role = pack.destination_roles["o2c_reporting_analyst"]
    core = next(r for r in role.requires if r.tier == "core")
    _, path = _plan(role.id, {core.skill: 2})
    assert all(s.skill != core.skill for s in path.steps)
    assert [p.target_level for p in path.practice_steps if p.skill == core.skill] == [3]
