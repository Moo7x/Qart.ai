"""Evidence-state rules (contract §4 SkillState v2) and the internal provisional estimate."""

import re

from src.contract import Event
from src.engine import params
from src.engine.skills import bkt_update, derive_skill_state, derive_states
from tests.helpers import golden_journey_events, make_event

SKILL = "unsupported_adjustment"
CHECKINS = ["checkin_001", "checkin_002", "checkin_003"]


def state_of(events: list[Event], self_confidence: float | None = None) -> str:
    return derive_skill_state("u_test", SKILL, events, self_confidence).state


# --- states ---------------------------------------------------------------------------------
def test_intake_claim_only_is_self_reported() -> None:
    result = derive_skill_state("u_aina", SKILL, [], 0.8)
    assert result.state == "self_reported"
    assert "8/10" in result.why
    assert result.counted_events == 0


def test_no_claim_and_no_events_is_insufficient_evidence() -> None:
    assert state_of([]) == "insufficient_evidence"


def test_one_counted_event_is_insufficient_evidence() -> None:
    assert state_of([make_event(1)], self_confidence=0.8) == "insufficient_evidence"


def test_success_with_help_gives_observed_with_help() -> None:
    events = [make_event(1, help_level=2), make_event(2, help_level=1)]
    assert state_of(events) == "observed_with_help"


def test_mixed_results_give_observed_with_help() -> None:
    events = [make_event(1, outcome="failure"), make_event(2, help_level=0)]
    assert state_of(events) == "observed_with_help"


def test_only_failures_stay_insufficient_evidence() -> None:
    events = [make_event(1, outcome="failure"), make_event(2, outcome="failure")]
    result = derive_skill_state("u_test", SKILL, events, None)
    assert result.state == "insufficient_evidence"
    assert "no success" in result.why


def test_two_independent_successes_incl_checkin_different_cases_and_sessions() -> None:
    events = [
        make_event(1, session_id="s_1"),
        make_event(2, session_id="s_2", mode="checkin", case_id="checkin_001"),
    ]
    result = derive_skill_state("u_test", SKILL, events, None)
    assert result.state == "demonstrated_independently"
    assert "not lasting mastery" in result.why
    assert result.next_to_confirm is None


def test_same_session_is_not_demonstrated() -> None:
    events = [
        make_event(1, session_id="s_1"),
        make_event(2, session_id="s_1", mode="checkin", case_id="checkin_001"),
    ]
    result = derive_skill_state("u_test", SKILL, events, None)
    assert result.state == "observed_with_help"
    assert "separate session" in result.why


def test_same_case_twice_is_not_demonstrated() -> None:
    events = [
        make_event(1, session_id="s_1", mode="checkin", case_id="checkin_001"),
        make_event(2, session_id="s_2", mode="checkin", case_id="checkin_001"),
    ]
    assert state_of(events) == "observed_with_help"


def test_no_checkin_is_not_demonstrated() -> None:
    events = [make_event(1, session_id="s_1"), make_event(2, session_id="s_2")]
    result = derive_skill_state("u_test", SKILL, events, None)
    assert result.state == "observed_with_help"
    assert "check-in" in result.why


def test_unaided_miss_after_successes_resets_demonstrated() -> None:
    events = [
        make_event(1, session_id="s_1"),
        make_event(2, session_id="s_2", mode="checkin", case_id="checkin_001"),
        make_event(3, session_id="s_3", outcome="failure"),
    ]
    result = derive_skill_state("u_test", SKILL, events, None)
    assert result.state == "observed_with_help"
    assert result.independent_successes == 0
    assert "case_003" in result.why


# --- flags ----------------------------------------------------------------------------------
def test_companion_error_event_does_not_count() -> None:
    events = [make_event(1, help_level=1), make_event(2, outcome="failure", companion_error=True)]
    result = derive_skill_state("u_test", SKILL, events, None)
    assert result.counted_events == 1
    assert result.state == "insufficient_evidence"
    flagged = [item for item in result.evidence_trail if not item.counted]
    assert [item.event_id for item in flagged] == ["ev_0002"]
    assert flagged[0].note is not None and "companion_error" in flagged[0].note


def test_ambiguous_case_event_does_not_count() -> None:
    events = [make_event(1, help_level=1), make_event(2, ambiguous_case=True)]
    assert derive_skill_state("u_test", SKILL, events, None).counted_events == 1


def test_data_issue_flag_alone_still_counts() -> None:
    events = [make_event(1, help_level=1), make_event(2, data_issue=True)]
    assert derive_skill_state("u_test", SKILL, events, None).counted_events == 2


def test_flagged_event_does_not_change_the_estimate() -> None:
    base = [make_event(1, help_level=1)]
    flagged = [*base, make_event(2, outcome="failure", companion_error=True)]
    a = derive_skill_state("u_test", SKILL, base, None).provisional_estimate
    b = derive_skill_state("u_test", SKILL, flagged, None).provisional_estimate
    assert a == b


# --- golden journey (contract §6 steps 2-4) --------------------------------------------------
def test_golden_journey_after_case_003_is_insufficient_evidence() -> None:
    events = golden_journey_events()[:1]
    assert derive_skill_state("u_aina", SKILL, events, 0.8).state == "insufficient_evidence"


def test_golden_journey_after_case_006_is_observed_with_help_zero_of_two() -> None:
    result = derive_skill_state("u_aina", SKILL, golden_journey_events()[:2], 0.8)
    assert result.state == "observed_with_help"
    assert result.independent_successes == 0
    assert result.why.startswith("0 of 2 independent successes.")


def test_golden_journey_after_checkin_is_one_of_two() -> None:
    result = derive_skill_state("u_aina", SKILL, golden_journey_events(), 0.8, CHECKINS)
    assert result.state == "observed_with_help"
    assert result.independent_successes == 1
    assert result.counted_events == 3
    assert result.why.startswith(
        "1 of 2 independent successes (checkin_001). "
        "Needs 1 more on a different case in a separate session. "
        "case_006 was solved after a question (help 1), so it counts as help-assisted."
    )
    assert "case_003" in result.why
    assert result.next_to_confirm == "checkin_002 (later session)"
    assert [(t.event_id, t.case_id, t.outcome, t.help_level) for t in result.evidence_trail] == [
        ("ev_0001", "case_003", "missed_then_found", 2),
        ("ev_0002", "case_006", "success", 1),
        ("ev_0003", "checkin_001", "success", 0),
    ]
    assert result.self_confidence == 0.8
    assert result.last_updated == "2026-10-22T10:40:00+08:00"


def test_golden_journey_second_checkin_in_new_session_is_demonstrated() -> None:
    events = golden_journey_events(include_second_checkin=True)
    result = derive_skill_state("u_aina", SKILL, events, 0.8, CHECKINS)
    assert result.state == "demonstrated_independently"
    assert result.independent_successes == 2


def test_derive_states_returns_one_state_per_skill() -> None:
    states = derive_states(
        "u_aina",
        ["unsupported_adjustment", "fx_conversion"],
        golden_journey_events(),
        {"unsupported_adjustment": 0.8},
    )
    assert [s.skill_id for s in states] == ["unsupported_adjustment", "fx_conversion"]
    assert states[1].state == "insufficient_evidence"


def test_no_user_facing_text_contains_a_percentage() -> None:
    for events in ([], golden_journey_events(), golden_journey_events(True)):
        why = derive_skill_state("u_aina", SKILL, events, 0.8, CHECKINS).why
        assert not re.search(r"\d\s*%", why)


# --- provisional estimate (internal) --------------------------------------------------------
def test_independent_success_raises_estimate_more_than_helped_success() -> None:
    prior = params.BKT_PRIOR
    assert bkt_update(prior, "success", 0) > bkt_update(prior, "success", 3)


def test_answer_shown_success_barely_moves_estimate_beyond_learning() -> None:
    prior = params.BKT_PRIOR
    learning_only = prior + (1 - prior) * params.BKT_LEARN
    assert abs(bkt_update(prior, "success", 4) - learning_only) < 0.02


def test_failure_lowers_estimate_before_learning() -> None:
    prior = 0.6
    assert bkt_update(prior, "failure", 0) < prior


def test_self_confidence_does_not_inflate_estimate() -> None:
    events = golden_journey_events()
    low = derive_skill_state("u_aina", SKILL, events, 0.1).provisional_estimate
    high = derive_skill_state("u_aina", SKILL, events, 1.0).provisional_estimate
    assert low == high
