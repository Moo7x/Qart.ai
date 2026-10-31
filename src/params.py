"""Declared parameters: every threshold the evidence layer uses, with its reason.

Each value is a *declared parameter* (a choice we state and can defend), not a measured fact.
Changing one changes labels on screen, so each change is logged in docs/decision_log.md.
"""

# --- OpenDOSM occupation shares ------------------------------------------------------------
# Evidence: DOSM's Labour Force tables classify occupations by MASCO 1998 up to 2010, MASCO 2008
# for 2011–2015 and MASCO 2013 from 2016 (Table 11 notes); the Salaries & Wages Survey behind
# OpenDOSM wages_occupation is run with the Labour Force Survey. Both changes show in the data:
# professionals jump 9.2% → 13.9% in 2011, and in 2016 four groups make their largest one-year
# move at once (professionals +2.8, service and sales −1.4, clerical −1.2, technicians +0.9
# points). Trends, trend models and forecasts therefore start at the latest change, 2016.
DOSM_FIRST_COMPARABLE_YEAR = 2016
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
# Forecasts (src/evidence/forecast.py). Horizons in steps of the series (years for OpenDOSM): one
# and two years, the app's scenario horizon. Declared parameter.
FORECAST_HORIZONS = (1, 2)
# Interval: the 10th and 90th percentile of the chosen model's backtest errors at that horizon,
# added to the forecast. Empirical, so it is only shown with at least this many errors.
INTERVAL_QUANTILES = (0.1, 0.9)
MIN_INTERVAL_ERRORS = 4
# Rolling backtest needs at least this many points before its first origin; a series with fewer
# points (e.g. job ads since the last coverage break) is shown without a forecast, and says why.
FORECAST_MIN_HISTORY = 6
# A model is used only if its error beats keeping the last value (relative error below 1);
# otherwise the forecast is the last value, labelled as such.
NAIVE_RATIO_TO_BEAT = 1.0
# Global gradient-boosting model (scikit-learn): learns the next yearly change from the last three
# changes and the level, across all occupation groups at once, so a short series borrows strength
# from the others. Needs this many training rows; a small, shallow model for ~15 yearly points.
GBR_LAGS = 3
GBR_MIN_TRAIN_ROWS = 20
GBR_MAX_DEPTH = 2
GBR_MAX_ITER = 100
GBR_RANDOM_STATE = 0  # fixed so the same data always gives the same forecast
# Watchdog: a run still marked "running" this long after it started is closed as interrupted.
# Longer than the pipeline lock (30 min, src/pipeline/run.py), so a live run is never closed.
RUN_WATCHDOG_MINUTES = 45
# Course catalogue (src/collectors/mslearn.py). For each pack skill the reranker scores the most
# similar catalogue items by meaning (query: the skill name alone) and the best few are kept.
# Read on 6 skills × 8 items (2026-10-30): the order was right, but good matches scored anywhere
# from 0.01 (SQL modules) to 0.95 (invoice processing), and clear mismatches scored below 0.01.
# So a skill keeps its top 5 above a 0.01 floor rather than everything above one fixed score.
# Every kept item is still a candidate (verified: false) until a reviewer opens it.
CATALOGUE_SHORTLIST = 15  # items per skill sent to the reranker
CATALOGUE_TOP_PER_SKILL = 5
CATALOGUE_MIN_RERANK = 0.01
CATALOGUE_MAX_SKILLS_PER_ITEM = 3  # an item is listed under at most its three best skills
# Automatic course fit check (src/collectors/course_check.py). Declared: a quote must be at least
# 5 words so a match is a real sentence, not a common phrase; the first 8,000 characters of a page
# hold a course's description and objectives; 20 s per page and 30 s per model call keep a check
# of ~100 candidates within a few minutes.
COURSE_CHECK_MIN_QUOTE_WORDS = 5
COURSE_CHECK_PAGE_CHARS = 8000
COURSE_CHECK_FETCH_SECONDS = 20
COURSE_CHECK_LLM_SECONDS = 30
# Resource scout (src/agents/scout.py). The agent may call at most 8 tools within 45 s, so a live
# run in the demo always ends; it reads at most 3 resources and keeps the 3 best segments of each.
# Video segments are 30–90 s of captions, cut at the end of a sentence: long enough to explain one
# idea, short enough to point at. Article passages are 300–900 characters.
AGENT_MAX_STEPS = 8
AGENT_TIME_BUDGET_SECONDS = 45.0
SCOUT_MAX_RESOURCES = 3
SCOUT_TOP_SEGMENTS = 3
SEGMENT_MIN_SECONDS = 30.0
SEGMENT_MAX_SECONDS = 90.0
PASSAGE_MIN_CHARS = 300
PASSAGE_MAX_CHARS = 900
FRAGMENT_WORDS = 8  # words that open a passage, used as its #:~:text= link anchor
# Progress check (src/agents/check.py): at least 2 and at most 4 questions before judging, enough
# for a concrete answer and one follow-up; a check can raise a level by at most 2 at once; a
# person can run 3 checks per skill per day, so the agent cannot be retried until it agrees.
CHECK_MIN_QUESTIONS = 2
CHECK_MAX_QUESTIONS = 4
CHECK_MAX_RAISE = 2
CHECKS_PER_SKILL_PER_DAY = 3
CHECK_MIN_QUOTE_CHARS = 8  # a quote shorter than this cannot show anything
# Privacy (src/privacy.py): a profile not updated for 90 days is deleted by the pipeline. Declared:
# long enough to come back to a plan after a quarter, short enough not to keep data for nothing.
PROFILE_RETENTION_DAYS = 90
# Status page: platform SDG totals are withheld while fewer people than this have a destination.
# Declared, from the project rule that aggregates across people suppress groups under 5.
PLATFORM_SDG_MIN_PROFILES = 5
# Prices for the cost estimate (status page, scripts/cost.py). Declared, not measured: the OpenAI
# list prices (USD per million tokens) checked on OpenAI's pricing page on 2026-10-31, and the
# RunPod Serverless GPU price from the endpoint's console on 2026-10-31. The endpoint may run on
# either of its two GPU tiers (16 GB: RTX 2000/4000 Ada, RTX A4000/A4500 at $0.58 per hour;
# 24 GB: RTX 3090, L4, RTX A5000 at $0.75 per hour), so the estimate uses the dearer one,
# $0.75 ÷ 3,600 s, and never understates the cost.
PRICES_PER_MILLION_TOKENS = {
    "gpt-4o-mini": {"in": 0.15, "out": 0.60},
    "gpt-4.1-mini": {"in": 0.40, "out": 1.60},
}
PRICES_CHECKED = "2026-10-31"
RUNPOD_USD_PER_HOUR = 0.75
RUNPOD_USD_PER_SECOND: float | None = RUNPOD_USD_PER_HOUR / 3600

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
# switchers always see them, since their claims rarely come from finance work yet. Data
# management is not in the list: keeping records clean shows no use of AI or automation tools.
AI_BASICS_SKILLS = (
    "prompt_engineering",
    "process_automation",
    "advanced_technology_integration",
)
AI_BASICS_SKIP_LEVEL = 3
AI_BASICS_ALWAYS = ("student", "switcher")
# No course labelled beginner is planned for a skill claimed at this level or above. Declared:
# "aware" (2) already covers what a beginner course teaches.
NO_BEGINNER_FROM_LEVEL = 2
