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

# --- DOSM job-ad releases --------------------------------------------------------------------
# A quarter-on-quarter change in the *total* number of online job offerings larger than this is
# treated as a change in platform coverage (a series break), not as demand. Q3 2025 rose 108.8%.
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
