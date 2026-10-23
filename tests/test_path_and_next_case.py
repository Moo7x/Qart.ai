"""Path planner and next-case targeting (Task A5), incl. the golden-journey path revision."""

import json
from pathlib import Path

from src.contract import Event, PathPlan, Profile, SkillState
from src.engine import params
from src.engine.catalogue import (
    CASE_INDEX_PATH,
    checkin_cases_by_skill,
    default_catalogue,
    load_case_index,
)
from src.engine.next_case import next_case
from src.engine.planner import AI_INTRO_NOTE, Resource, Selector, ai_intro_first, plan_path
from src.engine.planner_cpsat import cpsat_select
from src.engine.skills import derive_states
from tests.helpers import golden_journey_events

PROFILE_EXAMPLE = Path(__file__).resolve().parent.parent / "schemas" / "examples" / "profile.json"
ROLE = "ai_finops_analyst"
# These tests pin the planned case list (data/case_index.json) so their expected case ids stay
# fixed even when Person B's cases/index.json is present.
PLANNED_CASES = tuple(load_case_index(primary=CASE_INDEX_PATH))


def aina() -> Profile:
    return Profile.model_validate(json.loads(PROFILE_EXAMPLE.read_text(encoding="utf-8")))


def states_after(events: list[Event]) -> list[SkillState]:
    cat = default_catalogue()
    profile = aina()
    confidence = {s.skill_id: s.confidence for s in profile.skills_self_reported}
    checkins = checkin_cases_by_skill(PLANNED_CASES)
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
        PLANNED_CASES,
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
        PLANNED_CASES,
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

    # Before: learning steps (practice cases and/or a course), no check-in yet.
    assert adjustment_steps(before) and all(t != "checkin" for t, _ in adjustment_steps(before))
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


def test_real_grader_events_still_target_the_overconfident_skill_first() -> None:
    """Person B's grader records every skill of case_003 (incl. ai_output_review). Aina rated
    unsupported adjustments 8/10, so that mistake is practised first, then checked without help."""
    events = golden_journey_events()
    first = events[0].model_copy(deep=True)
    first.skills_evidence.append(
        first.skills_evidence[0].model_copy(update={"skill_id": "ai_output_review"})
    )
    case_id, because = next_after([first])
    assert case_id == "case_006" and "unsupported adjustments" in because
    second = events[1].model_copy(deep=True)
    second.skills_evidence.append(
        second.skills_evidence[0].model_copy(update={"skill_id": "ai_output_review"})
    )
    case_id, _ = next_after([first, second])
    assert case_id == "checkin_001"


def test_timeframe_sets_the_path_budget() -> None:
    # Planner budget = weekly_hours × horizon weeks (6 by default, the person's timeframe if set).
    cat = default_catalogue()
    states = states_after([])

    def plan(weeks: int) -> PathPlan:
        return plan_path(
            "u_aina",
            ROLE,
            1.0,
            states,
            cat,
            cat.assumptions_v1,
            PLANNED_CASES,
            set(),
            horizon_weeks=weeks,
        )

    short, long = plan(13), plan(52)
    assert short.total_hours <= 13 * 1.0
    # More time closes more of the worst-case gap (13 vs 52 weeks at 1 h/week).
    assert long.total_hours > short.total_hours
    assert long.worst_case_gap < short.worst_case_gap


def test_low_ai_comfort_moves_an_ai_intro_first_and_only_reorders() -> None:
    cat = default_catalogue()
    states = states_after([])

    def plan(comfort: int | None) -> PathPlan:
        return plan_path(
            "u_aina",
            ROLE,
            4.0,
            states,
            cat,
            cat.assumptions_v1,
            PLANNED_CASES,
            set(),
            ai_comfort=comfort,
        )

    base, low, high = plan(None), plan(2), plan(8)
    assert [s.ref for s in high.steps] == [s.ref for s in base.steps]
    assert sorted(s.ref for s in low.steps) == sorted(s.ref for s in base.steps)
    assert low.steps[0].ref in params.AI_INTRO_COURSES
    assert "2/10" in low.steps[0].because
    assert low.total_hours == base.total_hours


def test_ai_intro_already_first_is_not_reported_as_moved() -> None:
    """The comfort answer is only credited when it actually moved the course."""
    intro = sorted(params.AI_INTRO_COURSES)[0]
    first = Resource(id=intro, ref=intro, type="course", title="AI intro", hours=2, gains={})
    other = Resource(id="x", ref="x", type="course", title="Other", hours=5, gains={})
    unchanged = ai_intro_first([first, other], ai_comfort=2)
    assert unchanged == [first, other] and AI_INTRO_NOTE not in unchanged[0].because
    moved = ai_intro_first([other, first], ai_comfort=2)
    assert moved[0].id == intro and AI_INTRO_NOTE in moved[0].because
