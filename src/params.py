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

# --- Agents and forecasting (owner A, docs/PHASE2_PLAN.md §7) ---------------------------------
# Owner A adds parameters for the scout and progress-check agents, the change test, forecasting,
# privacy retention and the load test here.

# --- Matching (src/match/engine.py) ------------------------------------------------------------
# Bump when the formula/planning algorithm changes, even if its numeric parameters do not.
# Used with pack/parameter fingerprints to invalidate proposals computed under different rules.
CALCULATION_VERSION = "journey-3"  # journey-3: 0–5 described levels (C1); stored numbers kept
# Proficiency scale used everywhere (docs/PHASE2_PLAN.md §1 decision 2, aligned with SFIA's lower
# five levels): 0 none · 1 novice · 2 aware · 3 working · 4 proficient · 5 expert. Each level of
# each skill is described by an "I can…" sentence in data/packs/gbs_fa/levels.yaml.
PROFICIENCY_LABELS = ("none", "novice", "aware", "working", "proficient", "expert")
# Level a destination role needs, by requirement tier. Core skills are the role's defining work, so
# they need "working" (handles the full task alone); skills TalentCorp names for the move (upskill)
# and supporting tools need "aware" (routine tasks with guidance): enough to do the job while
# growing in it.
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
# Lowest scenario factor a weight can get. Declared: a routine skill can lose most of its weight
# but never vanish or turn negative, even at the 1.5 sensitivity intensity with 100% automation.
SCENARIO_FACTOR_FLOOR = 0.1
# Roles whose fit differs by less than this are near-ties: the person's interests may order them.
NEAR_TIE_POINTS = 3.0

# --- Decision support (src/match/decision.py) ----------------------------------------------------
# Level an unstated skill is assumed to have at the top of the fit range: "working", the
# highest level any requirement needs, so the range shows the most an answer could add. The bottom
# of the range is 0 (not stated counts as none, as in the fit itself).
UNSTATED_HIGH_LEVEL = 3
# Answers compared when choosing the most valuable question: none (0) versus working (3).
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
# Plan comparison (src/pathway/optimise.py): the time budget is the person's weekly hours over
# this many weeks, about one quarter; plans are compared within the same budget.
PLAN_BUDGET_WEEKS = 12
# Exact search enumerates every subset of the relevant courses; above this many it would be slow
# (2^16 = 65,536 subsets), so the comparison says it fell back to the greedy plan only.
PLAN_MAX_EXACT_COURSES = 16

# Today → Future you lists this many best-fitting roles for "now" and "after the plan". Declared
# display parameter: enough to show alternatives without turning the page into a second ranking.
FUTURE_ROLES_SHOWN = 3

# My plan splits reskilling into two tracks by the pack's declared skill kind: "data_digital"
# skills (data, systems, automation, prompting) form "Reskilling with AI"; finance, business and
# green skills form "Reskilling without AI". Declared parameter: the split follows TalentCorp's
# own skill clusters rather than a new judgement per skill.
AI_TRACK_KINDS = ("data_digital",)

# --- Levels and learning gain (owner B, docs/PHASE2_PLAN.md §6) -------------------------------
# Owner B adds parameters for the 0–5 level scale, fit range and bands, study versus practice,
# the adaptive plan, SDG totals and badges here (and edits the matching, decision and pathway
# sections above).

# CV reading (src/intake/extract.py, B1).
# ERP systems a CV may name. If the CV names one and no `erp` claim was read, a claim at
# ERP_RULE_LEVEL is added with that sentence as evidence: naming the system a person posted or
# reconciled in is direct evidence of using it. Declared list: the ERP and accounting systems
# common in Malaysian GBS and SME finance; matched as whole words, ignoring case.
ERP_ALIASES = (
    "SAP",
    "S/4HANA",
    "Oracle",
    "Dynamics 365",
    "NetSuite",
    "Workday Financials",
    "Infor",
    "Sage X3",
    "SQL Accounting",
    "AutoCount",
)
# Level of the rule's claim: "did it in a job" (2), the most a tool mention alone shows. Declared.
ERP_RULE_LEVEL = 2

# Level guide in the CV-reading prompt (src/intake/extract.py, B2). The scale meanings always go
# in; each skill's five sentences go in too when the whole guide stays under this many characters,
# otherwise the meanings only. Declared: about 2,000 tokens, so the prompt stays small and fast.
# Measured 2026-10-30: the 37 skills' sentences are about 16,500 characters, so today the prompt
# carries the meanings and rules only, and the person refines each level with its sentences.
LEVEL_GUIDE_MAX_CHARS = 8_000

# Fit band and "what would raise it" (src/match/decision.py, B3, docs/PHASE2_PLAN.md §4 C2).
# Band of a role's fit, from the fit itself. Declared thresholds, shown as an assumption: a fit of
# 75+ meets three quarters of the weighted requirements; below 35, most of the role is still to
# learn. Lower bound inclusive, checked from the top: strong ≥ 75 · good ≥ 55 · fair ≥ 35 · low.
BAND_THRESHOLDS = {"strong": 75, "good": 55, "fair": 35}
BAND_BELOW = "low"
# Highest level study alone can reach: "aware" (2). Levels 3 and above need work done (levels.yaml
# rule "done, not studied"). Declared: MQF counts 40 notional hours per credit including practice,
# and vendors expect months of use before working-level skill. Used by "raise" now and by the
# planner in B4.
STUDY_MAX_LEVEL = 2
RAISE_SHOWN = 3  # single-skill changes listed under "what would raise it"

# Study versus practice (src/pathway/planner.py, B4). These replace the old per-course gains.
# Material covering a skill gives level 1 ("novice") from LEVEL1_MIN_HOURS: enough to know the
# basics. Level 2 ("aware") needs LEVEL2_MIN_HOURS including at least one hands-on item: the
# shortest recognised programme found was 19 h (WSQ Vendor Performance Management). Declared.
# Study never goes above STUDY_MAX_LEVEL (above); levels 3 and 4 come from practice tasks.
LEVEL1_MIN_HOURS = 1
LEVEL2_MIN_HOURS = 20

# The plan adapts to the person (src/pathway/planner.py, B5). AI basics are skipped when the
# person already shows AI or automation work: any of these skills claimed at AI_BASICS_SKIP_LEVEL
# ("working") or above with evidence (a CV sentence or an accepted progress check). Declared: at
# that level they use these tools in their own work, which is what AI basics teach. Students and
# switchers always see them, since their claims rarely come from finance work yet.
AI_BASICS_SKILLS = (
    "prompt_engineering",
    "process_automation",
    "advanced_technology_integration",
    "data_management",
)
AI_BASICS_SKIP_LEVEL = 3
AI_BASICS_ALWAYS = ("student", "switcher")
# No course labelled beginner is planned for a skill claimed at this level or above. Declared:
# "aware" (2) already covers what a beginner course teaches.
NO_BEGINNER_FROM_LEVEL = 2
