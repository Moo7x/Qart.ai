# Evidence rules (`src/engine/skills.py`)

## 1. What it does
Turns an employee's case events into one **SkillState** per skill: a state name, a plain-language
`why`, and the evidence trail of cases behind it. No mastery percentage is ever shown.

## 2. Why it exists
Must-have 1 (intake + evidence) and the AGENTS.md rule "show evidence states, the cases behind them,
and why they changed". Help level is **evidence, not a measurement** (PROJECT_PLAN §5).

## 3. How it works
1. Collect every observation of the skill from the events (oldest first).
2. Events flagged `companion_error` or `ambiguous_case` stay in the trail with `counted: false` and
   never count for or against the skill. (`data_issue` alone still counts, per contract.)
3. States (declared rules, contract v2; constants in `params.py`):
   - **self_reported**: no counted events, only an intake claim.
   - **insufficient_evidence**: < 2 counted events, or only misses so far.
   - **demonstrated_independently**: ≥ 2 independent successes (help 0) on **different cases**, in
     **separate sessions**, at least one a **check-in**, all after the most recent unaided miss.
   - **observed_with_help**: everything else with ≥ 2 counted events and a success.
   A `missed_then_found` or `failure` outcome is an **unaided miss**: the employee tries alone first.
4. `why` = progress sentence ("1 of 2 independent successes (checkin_001). Needs 1 more on a different
   case in a separate session.") + help-assisted cases + misses + flagged events.
5. **Provisional estimate (internal only)**: help-weighted Bayesian knowledge tracing. Prior 0.20,
   learn 0.15, slip 0.10, guess by help level 0.15/0.30/0.50/0.75/0.95: a success after more help says
   less. Success: P(L)(1−S)/[P(L)(1−S)+(1−P(L))G_h]; miss (scored at help 0): P(L)S/[P(L)S+(1−P(L))(1−G_0)];
   then learning P ← P + (1−P)T. **All four are provisional assumptions without learner data.** It
   only orders practice (next case). Self-confidence is kept separate and never changes it.

## 4. Where in the code
`derive_skill_state`, `derive_states`, `qualifying_independent_successes`, `demonstrating_set`,
`explain`, `bkt_update`. Tests: `tests/test_skills.py` (one per transition + golden journey);
fixture `tests/fixtures/golden_journey_events.json`.

## 5. Example (golden journey, Aina, `unsupported_adjustment`, self-rated 8/10)
| After | State | Why (start) |
|---|---|---|
| intake | self_reported | Only your intake self-rating so far (8/10) |
| case_003 missed, found with hint (help 2) | insufficient_evidence | 1 counted event so far |
| case_006 success after a question (help 1) | observed_with_help | 0 of 2 independent successes |
| checkin_001 success, no help | observed_with_help | **1 of 2 independent successes (checkin_001)**, next: checkin_002 (later session) |
| optional checkin_002 in session s_0002 | demonstrated_independently | on these cases, not lasting mastery |

**Walk-backs without help (v2.1).** A wrong practice decision is held back; if the person then finds
the issue on their own, the event is `missed_then_found` at help 0. The "why" says "found on a second
look, without help". It still never counts as an independent success (`UNAIDED_MISS_OUTCOMES`). Before
v2.1 there was no wording for help 0, so the explanation crashed and `/api/skills` returned 500.

## 6. Limits and honesty
"Demonstrated" means on the listed cases, not lasting mastery. Rules and BKT parameters are not
calibrated with learner data; that needs a pilot (PROJECT_PLAN §10). Difficulty is recorded but not
used by the rules yet.

## 7. Questions and answers
- *Why not show a mastery %?* A number implies a measurement we don't have; the state + cases are
  checkable by the employee.
- *What if the companion was wrong?* The event is flagged and stops counting; the trail shows it.
- *Why two successes in separate sessions?* One success can be luck or short-term memory.
- *Does a hint-assisted success count?* Yes, as help-assisted evidence (observed with help), not as
  independent.

## 8. Design choices considered
Deep knowledge tracing (needs learner data we don't have); IRT (needs calibrated item difficulty);
a single threshold on the BKT estimate (opaque and uncalibrated, so it only orders practice).
