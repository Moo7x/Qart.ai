"""Path planner and next-case targeting (Task A5), incl. the golden-journey path revision."""

import json
from pathlib import Path

from src.contract import Event, PathPlan, Profile, SkillState
from src.engine.catalogue import checkin_cases_by_skill, default_case_index, default_catalogue
from src.engine.next_case import next_case
from src.engine.planner import Selector, plan_path
from src.engine.planner_cpsat import cpsat_select
from src.engine.skills import derive_states
from tests.helpers import golden_journey_events

PROFILE_EXAMPLE = Path(__file__).resolve().parent.parent / "schemas" / "examples" / "profile.json"
ROLE = "ai_finops_analyst"


def aina() -> Profile:
    return Profile.model_validate(json.loads(PROFILE_EXAMPLE.read_text(encoding="utf-8")))


def states_after(events: list[Event]) -> list[SkillState]:
    cat = default_catalogue()
    profile = aina()
    confidence = {s.skill_id: s.confidence for s in profile.skills_self_reported}
    checkins = checkin_cases_by_skill(default_case_index())
    return derive_states(profile.id, list(cat.skills), events, confidence, checkins)


def path_after(
    events: list[Event],
    weekly_hours: float,
    role_id: str = ROLE,
    selector: Selector | None = None,
) -> PathPlan:
    cat = default_catalogue()
    return plan_path(
        "u_aina",
        role_id,
        weekly_hours,
        states_after(events),
        cat,
        cat.assumptions_v1,
        default_case_index(),
        {e.case_id for e in events},
        selector,
    )


def next_after(events: list[Event]) -> tuple[str | None, str]:
    cat = default_catalogue()
    result = next_case(
        aina(),
        states_after(events),
        events,
        cat,
        cat.assumptions_v1,
        "assistive",
        default_case_index(),
    )
    return result.case_id, result.because


# --- next case ------------------------------------------------------------------------------
def test_after_case_003_next_case_targets_unsupported_adjustment() -> None:
    case_id, because = next_after(golden_journey_events()[:1])
    assert case_id == "case_006"
    assert "case_003" in because


def test_after_helped_success_next_case_is_a_no_help_checkin() -> None:
    case_id, because = next_after(golden_journey_events()[:2])
    assert case_id == "checkin_001"
    assert "case_006" in because and "check-in" in because


def test_after_checkin_the_next_open_mistake_moves_up() -> None:
    case_id, because = next_after(golden_journey_events())
    assert case_id == "case_009"
    assert "Transposition" in because and "case_003" in because


def test_next_case_never_repeats_a_seen_case() -> None:
    events = golden_journey_events()
    case_id, _ = next_after(events)
    assert case_id not in {e.case_id for e in events}


# --- path -----------------------------------------------------------------------------------
def test_path_fits_the_budget_and_respects_prerequisites() -> None:
    weekly_hours = 4
    plan = path_after([], weekly_hours)
    assert plan.total_hours <= weekly_hours * 6
    assert plan.robust_across == ["assistive", "agentic"]
    courses = default_catalogue().courses
    placed: set[str] = set()
    for step in plan.steps:
        if step.type == "course":
            assert set(courses[step.ref].prerequisites) <= placed
            assert step.url and step.retrieved
            assert courses[step.ref].verified
        placed.add(step.ref)
        assert step.sdg_targets


def test_smaller_weekly_budget_changes_the_plan() -> None:
    generous = path_after([], 4)
    tight = path_after([], 1)
    assert [s.ref for s in tight.steps] != [s.ref for s in generous.steps]
    assert tight.total_hours < generous.total_hours
    assert tight.worst_case_gap >= generous.worst_case_gap


def test_golden_journey_replaces_adjustments_module_with_one_confirmation_checkin() -> None:
    before = path_after([], 4)
    after = path_after(golden_journey_events(), 4)

    def adjustment_steps(plan: PathPlan) -> list[tuple[str, str]]:
        return [(s.type, s.ref) for s in plan.steps if "unsupported_adjustment" in s.skills]

    assert [t for t, _ in adjustment_steps(before)] == ["practice_case"]
    assert adjustment_steps(after) == [("checkin", "checkin_002")]
    checkin = next(s for s in after.steps if s.type == "checkin")
    assert checkin.because is not None and "1 of 2" in checkin.because
    assert after.worst_case_gap < before.worst_case_gap


def test_demonstrated_skill_drops_out_of_the_path() -> None:
    plan = path_after(golden_journey_events(include_second_checkin=True), 4)
    assert all("unsupported_adjustment" not in s.skills for s in plan.steps)


# --- CP-SAT (exact) version behind the same interface ---------------------------------------
def test_cpsat_is_never_worse_than_greedy_and_respects_constraints() -> None:
    courses = default_catalogue().courses
    for events in ([], golden_journey_events()):
        for weekly_hours in (1, 4):
            greedy = path_after(events, weekly_hours)
            exact = path_after(events, weekly_hours, selector=cpsat_select)
            assert exact.worst_case_gap <= greedy.worst_case_gap + 0.01
            assert exact.total_hours <= weekly_hours * 6
            placed: set[str] = set()
            for step in exact.steps:
                if step.type == "course":
                    assert set(courses[step.ref].prerequisites) <= placed
                placed.add(step.ref)


def test_cpsat_also_uses_the_confirmation_checkin() -> None:
    plan = path_after(golden_journey_events(), 4, selector=cpsat_select)
    steps = [(s.type, s.ref) for s in plan.steps if "unsupported_adjustment" in s.skills]
    assert steps == [("checkin", "checkin_002")]
