"""Declared parameters: every threshold the evidence layer uses, with its reason.

Each value is a *declared parameter* (a choice we state and can defend), not a measured fact.
Changing one changes labels on screen, so each change is logged in docs/decision_log.md.
"""

# --- OpenDOSM occupation shares ------------------------------------------------------------
# The occupation classification changed between 2010 and 2011 (professionals jump 9.2% → 13.9%),
# so trends start in 2011.
DOSM_FIRST_COMPARABLE_YEAR = 2011
# A group is labelled rising or weakening when its share of employees moved at least this many
# percentage points over the comparable period; smaller moves are within year-to-year noise
# (single-year swings of up to ~0.9 points occur, e.g. clerical 2019 → 2020).
DOSM_MIN_SHARE_CHANGE_PP = 0.5
# Backtest split: fit on years up to 2021, score on 2022–2025 (the four latest years).
BACKTEST_TRAIN_END = 2021
# Damping factor for the damped-trend model in the backtest (0 = no trend, 1 = straight line).
DAMPED_TREND_PHI = 0.7
DAMPED_TREND_FIT_YEARS = 5  # slope fitted on the last five training years
# Rolling-origin check (time-series cross-validation): first forecast origin and the horizons a
# forecast would be used for (the app's two-year scenario horizon and one year).
ROLLING_FIRST_ORIGIN = 2015
ROLLING_HORIZONS = (1, 2)
# Weight of the newest year in simple exponential smoothing; a common middle value, declared.
SMOOTHING_ALPHA = 0.5

# --- DOSM job-ad releases --------------------------------------------------------------------
# A quarter-on-quarter change in the *total* number of online job offerings larger than this is
# treated as a possible change in platform coverage (a series break), not as demand: DOSM does
# not explain such jumps, and the series covers only major private platforms. Q3 2025 rose 108.8%.
JOB_AD_BREAK_RATIO = 0.6

# --- Anthropic Economic Index ----------------------------------------------------------------
# Values are published rounded to 0.01, so a month-on-month change counts only if it is at least
# 5% relative AND at least 0.02 points; below that it may be rounding.
AEI_MIN_RELATIVE_CHANGE = 0.05
AEI_MIN_ABSOLUTE_CHANGE = 0.02

# --- Label gates -----------------------------------------------------------------------------
# A direction label (rising / weakening) needs either two independent sources agreeing, or one
# official series with at least this many comparable points. Otherwise the signal is shown as
# "not enough evidence yet", with its direction as an early signal.
MIN_INDEPENDENT_SOURCES = 2
MIN_POINTS_SINGLE_OFFICIAL_SERIES = 8

# --- Pipeline freshness --------------------------------------------------------------------
# If the newest run started longer ago than this, opening the app starts a background "catch-up"
# run. It backs up the scheduled job: DOSM publishes quarterly and the Economic Index irregularly,
# so one check a day is enough to notice a new release on the day it appears.
RUN_STALE_AFTER_HOURS = 24

# --- Matching (src/match/engine.py) ------------------------------------------------------------
# Bump when the formula/planning algorithm changes, even if its numeric parameters do not.
# Used with pack/parameter fingerprints to invalidate proposals computed under different rules.
CALCULATION_VERSION = "journey-2"  # journey-2: task-level AI-use evidence per requirement
# Proficiency scale used everywhere: 0 none · 1 aware · 2 working · 3 proficient · 4 expert.
PROFICIENCY_LABELS = ("none", "aware", "working", "proficient", "expert")
# Level a destination role needs, by requirement tier. Core skills are the role's defining work, so
# they need "proficient"; skills TalentCorp names for the move (upskill) and supporting tools need
# "working" level: enough to do the job while growing in it.
ROLE_TIER_LEVEL = {"core": 3, "upskill": 2, "support": 2}
# How much each tier counts in the fit score: defining work counts most, tools least.
ROLE_TIER_WEIGHT = {"core": 3.0, "upskill": 2.0, "support": 1.0}
# Scenario shift direction per skill's ai_role (data/packs/gbs_fa/skills.yaml): routine work loses
# weight as automation-style AI use reaches it; AI-complementing work gains weight.
AI_ROLE_DIRECTION = {"complement": 1, "routine": -1, "neutral": 0}
# Scenario intensity within the 2-year horizon: the share of the observed automation-style AI use
# assumed to reach these tasks. Moderate = half, fast = all of it. Declared, not estimated.
SCENARIO_INTENSITY = {"moderate": 0.5, "fast": 1.0}
SCENARIO_HORIZON_YEARS = 2
# Roles whose fit differs by less than this are near-ties: the person's interests may order them.
NEAR_TIE_POINTS = 3.0

# --- Decision support (src/match/decision.py) ----------------------------------------------------
# Level an unstated skill is assumed to have at the top of the fit range: "proficient", the
# highest level any requirement needs, so the range shows the most an answer could add. The bottom
# of the range is 0 (not stated counts as none, as in the fit itself).
UNSTATED_HIGH_LEVEL = 3
# Answers compared when choosing the most valuable question: none (0) versus proficient (3).
QUESTION_ANSWERS = (0, 3)
QUESTIONS_SHOWN = 3
# Ranking of questions: an essential of the person's chosen (else best-fitting) role matters most,
# because it decides whether their own goal is a longer route; next, an answer that would change
# their best-fitting role; then the largest fit swing (in points) as a tie-break.
QUESTION_WEIGHT_GOAL_ESSENTIAL = 150.0
QUESTION_WEIGHT_TOP_CHANGE = 100.0
# Adoption intensities for the sensitivity check: no AI shift, the two declared scenarios, and a
# stronger-than-fast case, so the person sees which ranks depend on that assumption.
SENSITIVITY_INTENSITIES = (0.0, 0.25, 0.5, 0.75, 1.0, 1.5)

# --- Pathway (src/pathway/planner.py) ----------------------------------------------------------
# Highest level a course's material can take a skill to, by its stated level.
COURSE_LEVEL_REACH = {"beginner": 2, "intermediate": 3, "advanced": 3}
# Most levels a single course can add to a skill, by its length. Short modules introduce a topic;
# only longer material can move someone two levels. Several courses on one skill add up, capped by
# each course's level reach. Declared to keep plans honest about what a few hours can do.
COURSE_SHORT_MINUTES = 180
COURSE_MAX_GAIN_SHORT = 1
COURSE_MAX_GAIN_LONG = 2
# Plan comparison (src/pathway/optimise.py): the time budget is the person's weekly hours over
# this many weeks, about one quarter; plans are compared within the same budget.
PLAN_BUDGET_WEEKS = 12
# Exact search enumerates every subset of the relevant courses; above this many it would be slow
# (2^16 = 65,536 subsets), so the comparison says it fell back to the greedy plan only.
PLAN_MAX_EXACT_COURSES = 16

# Today → Future you lists this many best-fitting roles for "now" and "after the plan". Declared
# display parameter: enough to show alternatives without turning the page into a second ranking.
FUTURE_ROLES_SHOWN = 3
