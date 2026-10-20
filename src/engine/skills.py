"""Evidence rules: events → SkillState (contract §4 SkillState rules, v2).

The user-facing state comes ONLY from the explicit rules below; the provisional estimate is an
internal number used to order practice and is never shown as a percentage.

Rules (contract v2, with the edge cases in docs/CONTRACT_QUESTIONS.md Q1/Q3):
- Events flagged companion_error or ambiguous_case are kept in the trail but do not count.
- self_reported: no counted events, only an intake claim.
- insufficient_evidence: fewer than 2 counted events (or no claim at all), or only misses so far.
- demonstrated_independently: ≥2 independent successes (help 0) on different cases, in separate
  sessions, at least one a check-in, with no unaided miss since (only successes after the most
  recent miss qualify).
- observed_with_help: everything else with ≥2 counted events and at least one success.
"""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import datetime
from itertools import combinations

from src.contract import (
    CaseMode,
    Event,
    EvidenceTrailItem,
    FlagName,
    Outcome,
    SkillState,
    SkillStateName,
)
from src.engine import params

UNAIDED_MISS_OUTCOMES: frozenset[Outcome] = frozenset({"missed_then_found", "failure"})
NOT_COUNTED_FLAGS: tuple[FlagName, ...] = ("companion_error", "ambiguous_case")
SELF_RATING_SCALE = 10  # intake confidence 0..1 is shown as the employee's own n/10 rating
HELP_PHRASE: dict[int, str] = {
    1: "after a question",
    2: "after a hint",
    3: "after an explanation",
    4: "only after the answer was shown",
}


@dataclass(frozen=True)
class Observation:
    """One event's evidence about one skill."""

    event_id: str
    case_id: str
    session_id: str
    mode: CaseMode
    timestamp: str
    outcome: Outcome
    help_level: int
    flag: FlagName | None

    @property
    def counted(self) -> bool:
        return self.flag is None

    @property
    def is_independent_success(self) -> bool:
        return self.outcome == "success" and self.help_level == params.INDEPENDENT_HELP_LEVEL

    @property
    def is_unaided_miss(self) -> bool:
        # The employee always tries alone first (PROJECT_PLAN §1), so any miss is an unaided miss.
        return self.outcome in UNAIDED_MISS_OUTCOMES


def _flag_that_excludes(event: Event) -> FlagName | None:
    for flag in NOT_COUNTED_FLAGS:
        if getattr(event.flags, flag):
            return flag
    return None


def observations_for(skill_id: str, events: Iterable[Event]) -> list[Observation]:
    """All observations of `skill_id`, oldest first."""
    found = [
        Observation(
            event_id=event.id,
            case_id=event.case_id,
            session_id=event.session_id,
            mode=event.mode,
            timestamp=event.timestamp,
            outcome=evidence.outcome,
            help_level=evidence.help_level,
            flag=_flag_that_excludes(event),
        )
        for event in events
        for evidence in event.skills_evidence
        if evidence.skill_id == skill_id
    ]
    return sorted(found, key=lambda o: datetime.fromisoformat(o.timestamp))


# --- provisional estimate (internal) --------------------------------------------------------
def bkt_update(p_known: float, outcome: Outcome, help_level: int) -> float:
    """One help-weighted Bayesian knowledge tracing step.

    success:  P(L|obs) = P(L)(1−S) / [P(L)(1−S) + (1−P(L))·G_h]
    miss:     P(L|obs) = P(L)·S   / [P(L)·S   + (1−P(L))·(1−G_0)]
    learning: P(L) ← P(L|obs) + (1 − P(L|obs))·T
    A miss is scored at help 0 because it happened before any help was given.
    """
    slip, learn = params.BKT_SLIP, params.BKT_LEARN
    if outcome == "success":
        guess = params.BKT_GUESS_BY_HELP[help_level]
        hit = p_known * (1 - slip)
        posterior = hit / (hit + (1 - p_known) * guess)
    else:
        guess = params.BKT_GUESS_BY_HELP[params.INDEPENDENT_HELP_LEVEL]
        miss = p_known * slip
        posterior = miss / (miss + (1 - p_known) * (1 - guess))
    return posterior + (1 - posterior) * learn


def provisional_estimate(counted: Sequence[Observation]) -> float:
    p_known = params.BKT_PRIOR
    for obs in counted:
        p_known = bkt_update(p_known, obs.outcome, obs.help_level)
    return round(p_known, params.ESTIMATE_DECIMALS)


# --- rules ----------------------------------------------------------------------------------
def qualifying_independent_successes(counted: Sequence[Observation]) -> list[Observation]:
    """Independent successes after the most recent unaided miss ("no independent failure since")."""
    last_miss = max((i for i, o in enumerate(counted) if o.is_unaided_miss), default=-1)
    return [o for o in counted[last_miss + 1 :] if o.is_independent_success]


def demonstrating_set(qualifying: Sequence[Observation]) -> tuple[Observation, ...] | None:
    """A set of successes meeting the rule (different cases, separate sessions, ≥1 check-in)."""
    needed = params.REQUIRED_INDEPENDENT_SUCCESSES
    for combo in combinations(qualifying, needed):
        different_cases = len({o.case_id for o in combo}) == needed
        separate_sessions = len({o.session_id for o in combo}) == needed
        checkins = sum(o.mode == "checkin" for o in combo)
        if different_cases and separate_sessions and checkins >= params.REQUIRED_CHECKIN_SUCCESSES:
            return combo
    return None


def _decide_state(counted: Sequence[Observation], self_confidence: float | None) -> SkillStateName:
    if not counted:
        return "self_reported" if self_confidence is not None else "insufficient_evidence"
    if len(counted) < params.MIN_COUNTED_EVENTS:
        return "insufficient_evidence"
    if not any(o.outcome == "success" for o in counted):
        return "insufficient_evidence"
    if demonstrating_set(qualifying_independent_successes(counted)):
        return "demonstrated_independently"
    return "observed_with_help"


# --- plain-language "why" -------------------------------------------------------------------
def _cases(observations: Iterable[Observation]) -> str:
    return ", ".join(o.case_id for o in observations)


def _progress_sentence(qualifying: Sequence[Observation]) -> str:
    needed = params.REQUIRED_INDEPENDENT_SUCCESSES
    count = len(qualifying)
    has_checkin = any(o.mode == "checkin" for o in qualifying)
    if count == 0:
        return (
            f"0 of {needed} independent successes. Needs {needed} no-help successes on different "
            "cases in separate sessions, at least one a check-in."
        )
    if count < needed:
        text = (
            f"{count} of {needed} independent successes ({_cases(qualifying)}). Needs "
            f"{needed - count} more on a different case in a separate session."
        )
        return text if has_checkin else text + " At least one must be a no-help check-in."
    problems = []
    if len({o.case_id for o in qualifying}) < needed:
        problems.append("all on the same case")
    if len({o.session_id for o in qualifying}) < needed:
        problems.append("all in the same session")
    if not has_checkin:
        problems.append("none is a check-in")
    return (
        f"{count} independent successes ({_cases(qualifying)}), but {' and '.join(problems)}. "
        "Needs 1 more on a different case in a separate session"
        + ("." if has_checkin else ", as a no-help check-in.")
    )


def _detail_sentences(observations: Sequence[Observation], counted: Sequence[Observation]) -> str:
    sentences = []
    for obs in counted:
        if obs.outcome == "success" and obs.help_level > params.INDEPENDENT_HELP_LEVEL:
            sentences.append(
                f"{obs.case_id} was solved {HELP_PHRASE[obs.help_level]} "
                f"(help {obs.help_level}), so it counts as help-assisted."
            )
    for obs in counted:
        if obs.outcome == "missed_then_found":
            sentences.append(
                f"{obs.case_id} was missed at first, then found {HELP_PHRASE[obs.help_level]} "
                f"(help {obs.help_level})."
            )
        elif obs.outcome == "failure":
            sentences.append(f"{obs.case_id} was missed (help {obs.help_level}).")
    flagged = [o for o in observations if not o.counted]
    if flagged:
        listed = ", ".join(f"{o.event_id} ({o.flag})" for o in flagged)
        sentences.append(f"{len(flagged)} flagged event(s) not counted: {listed}.")
    return " ".join(sentences)


def _reset_sentence(counted: Sequence[Observation]) -> str:
    last_miss = max((i for i, o in enumerate(counted) if o.is_unaided_miss), default=-1)
    earlier = [o for o in counted[:last_miss] if o.is_independent_success]
    if last_miss < 0 or not earlier:
        return ""
    return f"An unaided miss on {counted[last_miss].case_id} reset the independent-success count."


def explain(
    state: SkillStateName,
    observations: Sequence[Observation],
    self_confidence: float | None,
) -> str:
    counted = [o for o in observations if o.counted]
    qualifying = qualifying_independent_successes(counted)
    if state == "self_reported":
        rating = round((self_confidence or 0.0) * SELF_RATING_SCALE)
        head = (
            f"Only your intake self-rating so far ({rating}/{SELF_RATING_SCALE}); "
            "no case evidence yet."
        )
    elif state == "insufficient_evidence" and not counted:
        head = "No case evidence yet."
    elif state == "insufficient_evidence" and len(counted) < params.MIN_COUNTED_EVENTS:
        head = (
            f"{len(counted)} counted event so far; at least {params.MIN_COUNTED_EVENTS} are "
            "needed before we say anything."
        )
    elif state == "insufficient_evidence":
        head = f"{len(counted)} counted events but no success observed yet; keep practising."
    elif state == "demonstrated_independently":
        combo = demonstrating_set(qualifying) or ()
        head = (
            f"Demonstrated independently on these cases: {_cases(combo)} (no help, different "
            "cases, separate sessions, no unaided miss since). This means on these cases, "
            "not lasting mastery."
        )
    else:
        head = _progress_sentence(qualifying)
    parts = [head, _reset_sentence(counted), _detail_sentences(observations, counted)]
    return " ".join(p for p in parts if p)


def _next_to_confirm(
    state: SkillStateName,
    observations: Sequence[Observation],
    checkin_case_ids: Sequence[str],
) -> str | None:
    if state != "observed_with_help":
        return None
    seen = {o.case_id for o in observations}
    unseen = [case_id for case_id in checkin_case_ids if case_id not in seen]
    if not unseen:
        return None
    counted = [o for o in observations if o.counted]
    later = " (later session)" if qualifying_independent_successes(counted) else ""
    return f"{unseen[0]}{later}"


def _trail_item(obs: Observation) -> EvidenceTrailItem:
    return EvidenceTrailItem(
        event_id=obs.event_id,
        case_id=obs.case_id,
        outcome=obs.outcome,
        help_level=obs.help_level,
        counted=obs.counted,
        note=None if obs.counted else f"not counted: flagged {obs.flag}",
    )


def derive_skill_state(
    user_id: str,
    skill_id: str,
    events: Iterable[Event],
    self_confidence: float | None,
    checkin_case_ids: Sequence[str] = (),
) -> SkillState:
    """Apply the evidence rules to one skill.

    Args:
        user_id: the employee.
        skill_id: catalogue skill id.
        events: the employee's events (any order; other skills are ignored).
        self_confidence: intake self-rating 0..1, or None if no claim. Kept separate: it never
            changes the state or the estimate.
        checkin_case_ids: check-in cases that practise this skill, used for `next_to_confirm`.
    """
    observations = observations_for(skill_id, events)
    counted = [o for o in observations if o.counted]
    state = _decide_state(counted, self_confidence)
    return SkillState(
        user_id=user_id,
        skill_id=skill_id,
        state=state,
        why=explain(state, observations, self_confidence),
        next_to_confirm=_next_to_confirm(state, observations, checkin_case_ids),
        evidence_trail=[_trail_item(o) for o in observations],
        counted_events=len(counted),
        independent_successes=len(qualifying_independent_successes(counted)),
        self_confidence=self_confidence,
        provisional_estimate=provisional_estimate(counted),
        estimate_note=params.ESTIMATE_NOTE,
        last_updated=counted[-1].timestamp if counted else None,
    )


def derive_states(
    user_id: str,
    skill_ids: Sequence[str],
    events: Sequence[Event],
    self_confidence: dict[str, float],
    checkin_cases_by_skill: dict[str, list[str]] | None = None,
) -> list[SkillState]:
    """SkillStates for every skill in `skill_ids`, in that order."""
    checkins = checkin_cases_by_skill or {}
    return [
        derive_skill_state(
            user_id, skill_id, events, self_confidence.get(skill_id), checkins.get(skill_id, [])
        )
        for skill_id in skill_ids
    ]
