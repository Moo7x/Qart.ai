"""Pathways use only verified courses, respect prerequisites and hours, and cite SDG targets."""

import pytest

from src.match.engine import score_role
from src.pack import load_pack
from src.pathway.planner import plan_pathway
from tests.test_match import EVIDENCE, NUR


def nur_path(role_id: str, weekly_hours: float = 6) -> object:
    pack = load_pack()
    match = score_role(pack, pack.destination_roles[role_id], NUR, "moderate", EVIDENCE)
    return plan_pathway(pack, match, NUR, weekly_hours, "moderate", EVIDENCE)


def test_every_step_is_a_verified_course_and_prerequisites_come_first() -> None:
    pack = load_pack()
    path = nur_path("o2c_reporting_analyst")
    ids = [s.course.id for s in path.steps]  # type: ignore[attr-defined]
    assert all(i in pack.courses for i in ids)
    for position, course_id in enumerate(ids):
        for prereq in pack.courses[course_id].requires:
            assert prereq in ids[:position]


def test_no_course_is_taken_twice() -> None:
    path = nur_path("finance_systems_analyst")
    ids = [s.course.id for s in path.steps]  # type: ignore[attr-defined]
    assert len(ids) == len(set(ids))


def test_weeks_follow_the_weekly_hours() -> None:
    slow = nur_path("o2c_reporting_analyst", weekly_hours=2)
    fast = nur_path("o2c_reporting_analyst", weekly_hours=10)
    assert slow.total_hours == fast.total_hours  # type: ignore[attr-defined]
    assert slow.weeks > fast.weeks  # type: ignore[attr-defined]


def test_fit_after_the_path_is_not_lower_and_gaps_without_courses_are_named() -> None:
    path = nur_path("compliance_governance_specialist")
    assert path.fit_after >= path.fit_before  # type: ignore[attr-defined]
    assert "Internal Controls Evaluation" in path.uncovered  # type: ignore[attr-defined]


def test_every_step_and_the_path_carry_sdg_targets_with_a_reason() -> None:
    path = nur_path("o2c_reporting_analyst")
    for step in path.steps:  # type: ignore[attr-defined]
        assert step.sdgs, step.course.id
        assert all(s.how for s in step.sdgs)
    assert {"4.3", "8.5"} <= set(path.sdg_summary)  # type: ignore[attr-defined]


def test_weekly_hours_must_be_positive() -> None:
    with pytest.raises(ValueError):
        nur_path("cost_accountant", weekly_hours=0)
