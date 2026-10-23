"""Every weight, threshold and parameter the engine uses, in one place.

Each constant says what it is, why it has this value, and its status:
- DECLARED: a design choice fixed in the team contract / PROJECT_PLAN (not fitted to data).
- ASSUMPTION: a provisional value with no data behind it yet; disclosed to users and reviewers.
- SOURCED: taken from a cited external source.

Company adoption assumptions (task allocation, shift fractions) are NOT here: they are layer B,
owned and edited by HR in catalogue/company_assumptions.json.
"""

from typing import Final

from src.contract import SkillStateName

# --- Evidence rules (contract §4 SkillState rules, v2) ----------------------------------------
# DECLARED (contract): with fewer counted events we cannot say anything about the skill.
MIN_COUNTED_EVENTS: Final = 2
# DECLARED (contract): independent successes needed for "demonstrated_independently".
REQUIRED_INDEPENDENT_SUCCESSES: Final = 2
# DECLARED (contract): at least one of those successes must be a no-help check-in.
REQUIRED_CHECKIN_SUCCESSES: Final = 1
# DECLARED (contract §3): help level 0 = "none"; only this counts as independent.
INDEPENDENT_HELP_LEVEL: Final = 0

# --- Provisional estimate: help-weighted Bayesian knowledge tracing (Task A3) -----------------
# ASSUMPTION: all four are provisional. No learner data was available to fit them. The estimate
# only orders practice; it never decides the user-facing state and is never shown as a %.
BKT_PRIOR: Final = 0.20  # P(L0): most new hires have not yet shown this review skill
BKT_LEARN: Final = 0.15  # T: chance of learning the skill from one practised case
BKT_SLIP: Final = 0.10  # S: chance a skilled person still misses an error
# G_h by help level 0..4: more help → a success says less about the person (help is evidence,
# not a measurement). At level 4 the answer was shown, so a "success" is almost pure guess.
BKT_GUESS_BY_HELP: Final = (0.15, 0.30, 0.50, 0.75, 0.95)
ESTIMATE_NOTE: Final = (
    "internal, used only to order practice; parameters are provisional assumptions "
    "(no learner data was available to fit them)"
)
# DECLARED: rounding for the internal estimate (2 decimals, as in the contract example).
ESTIMATE_DECIMALS: Final = 2

# --- Recommender (PROJECT_PLAN §6, contract Recommendation v2) --------------------------------
# DECLARED: additive score; effort is a PENALTY (subtracted). A ±20% sensitivity test is run.
SCORE_WEIGHT_COVERAGE: Final = 0.55  # evidence that the person already has the role's skills
SCORE_WEIGHT_CONFIDENCE: Final = 0.20  # how much of that is backed by ≥2 counted events
SCORE_WEIGHT_INTEREST: Final = 0.10  # people choose their direction; interest matters, a bit
SCORE_WEIGHT_EFFORT: Final = 0.15  # penalty: hours needed to close the gaps
SCORE_FORMULA: Final = "0.55*coverage + 0.20*confidence + 0.10*interest - 0.15*effort"
# Shown next to every score in the UI, so it stays short.
SCORE_NOTE: Final = (
    "Suitability indicator, not a probability. Hours still needed count as a penalty, so a "
    "score below 0 is shown as 0 (the ranking still uses the real value)."
)
# DECLARED: displayed scores never go below this (the UI never shows negative scores).
SCORE_DISPLAY_FLOOR: Final = 0.0
# DECLARED: fit = (0.55·coverage + 0.20·confidence + 0.10·interest) / 0.85, i.e. the score
# without the effort penalty, rescaled to 0–1 by the sum of the positive weights.
FIT_DECIMALS: Final = 2
TIME_TO_READY_DECIMALS: Final = 1
# DECLARED: the top two roles are a "close match" when their (unclamped) scores differ by less
# than 0.03. Rule: halfway between the largest top-two gap that flips under ±20% weight changes
# (0.02 in the first run, 0.013 after the course update) and the smallest gap that stays stable
# (0.033 after the course update) in eval/SENSITIVITY.md. Re-derive it when the data changes.
CLOSE_MATCH_THRESHOLD: Final = 0.03
# DECLARED: credit per evidence state. Help-assisted evidence counts half; a self-report counts a
# little (it is a claim, not evidence); no evidence counts nothing.
STATE_CREDIT: Final[dict[SkillStateName, float]] = {
    "demonstrated_independently": 1.0,
    "observed_with_help": 0.5,
    "self_reported": 0.2,
    "insufficient_evidence": 0.0,
}
# DECLARED: "confidence" counts a skill as evidenced once it has this many counted events.
CONFIDENCE_MIN_EVENTS: Final = MIN_COUNTED_EVENTS
# DECLARED: effort = hours to close gaps / (weekly_hours × 12 weeks), capped at 1.
EFFORT_HORIZON_WEEKS: Final = 12
EFFORT_CAP: Final = 1.0
# DECLARED: decimals for scores and factors in API output (readability, not precision).
SCORE_DECIMALS: Final = 2
WEIGHT_DECIMALS: Final = 2

# --- Path planner (Task A5) -------------------------------------------------------------------
# DECLARED: the plan must fit weekly_hours × 6 weeks.
PLAN_HORIZON_WEEKS: Final = 6
# ASSUMPTION: each covering resource is assumed to close 0.3 of a skill's gap. Coverage is not
# demonstrated skill: the state only changes when new case evidence arrives.
RESOURCE_GAIN: Final = 0.3
# ASSUMPTION: a confirmation check-in, if passed, moves a skill from "observed with help with
# 1 of 2 independent successes" to "demonstrated" (credit 0.5 → 1.0), so its expected gain is
# the full remaining gap. It is evidence collection, not learning.
CHECKIN_GAIN: Final = 0.5
# ASSUMPTION: time for a bundle of 3 in-app practice cases (≈30 min per case, our case design).
PRACTICE_BUNDLE_HOURS: Final = 1.5
PRACTICE_BUNDLE_CASES: Final = 3
# ASSUMPTION: time for one no-help check-in case.
CHECKIN_HOURS: Final = 0.5
# DECLARED: a planner step must reduce the worst-case gap by more than this to be worth adding.
MIN_GAP_IMPROVEMENT: Final = 1e-9

# --- Profile answers that shape the path (contract v2.2) -----------------------------------
# DECLARED: the person's own timeframe (Profile.preferences.timeframe_months) replaces both
# horizons above when set: weeks = months × 52/12, rounded (3 → 13, 6 → 26, 12 → 52). It is the
# person's plan, not a forecast. Without it the fixed 6 (path) and 12 (effort) weeks apply.
WEEKS_PER_MONTH: Final = 52 / 12
# DECLARED: AI comfort (0..10, self-rated) at or below this puts an AI-intro course first in the
# path when the planner already chose one; it never adds a course the planner did not choose.
AI_COMFORT_LOW: Final = 3
# DECLARED: courses that introduce AI tools from scratch (catalogue/courses.json, verified),
# in no particular order; the shortest chosen one is placed first.
AI_INTRO_COURSES: Final = ("course_25", "course_14", "course_15")

# --- Course cost preference (brief: "free or low-cost resources") ---------------------------
# DECLARED: the company funds training, so verified paid courses may appear in a path, but free
# and low-cost ones are preferred. Tiers come from the course's cost label: a label starting with
# "free" → 0, "low-cost" → 1, anything else (paid, or no price stated) → 2, so a course is never
# treated as free unless its label says so (and courses.json records the cost_source).
COST_TIER_FREE: Final = 0
COST_TIER_LOW: Final = 1
COST_TIER_PAID_OR_UNKNOWN: Final = 2
FREE_COST_PREFIX: Final = "free"
LOW_COST_PREFIX: Final = "low-cost"
# Rule 1 (dominance): a course is dropped from the candidates when another verified course covers
# all of the same skill gaps for the role at a lower cost tier.
# Rule 2 (tie-break): when two candidates cut the worst-case gap equally per hour, the lower cost
# tier wins, then the id.

# --- HR aggregates (AGENTS.md privacy rule) ---------------------------------------------------
# DECLARED: groups and cells under 5 people are suppressed. This reduces but does not eliminate
# re-identification risk.
HR_MIN_GROUP_SIZE: Final = 5
# DECLARED: a skill is in a scenario's training demand when some internal role weights it at
# least this much (normalised weight) under that scenario.
HR_DEMAND_MIN_WEIGHT: Final = 0.05

# --- Role outlook (brief: "predict which jobs emerge or decline") ----------------------------
# Derived from company assumptions (layer B), never a headcount forecast.
# DECLARED: a role is "being transformed" when at least half of its task weight is done or
# drafted by AI under the scenario: most of its current doing-work turns into checking.
OUTLOOK_TRANSFORMED_AI_SHARE: Final = 0.5
# DECLARED: otherwise it is an "AI-era role" when at least 60% of its skill weight is oversight
# (reviewing AI output, judgment, controls): it grows with AI while its own tasks stay human.
OUTLOOK_AI_ERA_OVERSIGHT_SHARE: Final = 0.6
OUTLOOK_BASIS: Final = (
    "derived from company assumptions (layer B); describes how tasks shift, "
    "not a headcount forecast"
)
OUTLOOK_DECIMALS: Final = 2

# --- Snapshot diff (Task A1) ------------------------------------------------------------------
# DECLARED: a signal "changed" when its relative change is at least 5% AND its absolute change is at
# least 0.02 (percentage points). AEI publishes values rounded to two decimals, so a 0.01 step on a
# small share (0.11 → 0.12) can be rounding alone. Smaller moves do not trigger a review.
SIGNAL_REVIEW_RELATIVE_CHANGE: Final = 0.05
SIGNAL_REVIEW_MIN_ABS_CHANGE: Final = 0.02
SIGNAL_DECIMALS: Final = 4

# --- Retrieval (src/retrieval, RAG preparation; not used by the planner yet) ----------------
# SOURCED: standard Okapi BM25 defaults (Robertson & Zaragoza, 2009): term-frequency saturation
# k1 = 1.5 and length normalisation b = 0.75. Not tuned on our evaluation set.
BM25_K1: Final = 1.5
BM25_B: Final = 0.75
# SOURCED: reciprocal-rank fusion constant k = 60 (Cormack, Clarke & Büttcher, SIGIR 2009).
RRF_K: Final = 60
# DECLARED: results returned by default and the cut-off for recall@k in eval/retrieval_eval.py.
RETRIEVAL_TOP_K: Final = 5
