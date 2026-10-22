# Trend snapshots and diff (`src/engine/snapshots.py`, `src/engine/ingest.py`)

## 1. What it does
Turns the public Anthropic Economic Index (AEI) release into **dated snapshots** of AI usage on
finance occupations (GLOBAL and Malaysia), compares two snapshots, and **suggests which company
assumptions HR should review**. It never changes skill weights.

## 2. Why it exists
Must-have 2 (dated signals with source/date and diff) and the success test "visible change when
trend data changes" (golden journey step 6). Layer A of PROJECT_PLAN §6.

## 3. How it works
1. `ingest.py` downloads `release_2026_06_26/data/aei_claude_ai_2026-06-26.csv` (~220 MB) into
   `data/raw/` (gitignored) and keeps: geo GLOBAL/MYS; SOC detailed occupations 43-3031, 13-2011,
   13-2051, 13-2031, 43-3051, 43-3021, 13-1041, 15-2051, 43-9111 (`.00` codes only); metrics `pct`
   (→ `usage_pct`: share % of the geography's conversations), automation/augmentation shares; and
   country-level automation/augmentation.
2. One snapshot per month (2026-04, 2026-05) → `data/snapshots/snap_aei_2026_0X.json` with source,
   URL, release date, retrieval date, licence (CC-BY) and the label "historical data replay".
3. `diff()`: a signal is significant when it moves ≥ 5% relative **and** ≥ 0.02 absolute (*declared*;
   AEI rounds to 2 decimals, so 0.11 → 0.12 can be rounding). Significant signals are matched to the
   `review_triggers` in `company_assumptions.json` → `suggested_assumption_reviews` with a reason.
4. HR (synthetic) approves a change with `PUT /api/assumptions`; only then do weights change.

## 4. Where in the code
`build_snapshot`, `compare_signals`, `diff`, `diff_report`, `load_snapshots` (pure);
`run_ingest`, `read_finance_rows`, `download_release` (I/O, `python -m src.engine.ingest`, schedulable).
Tests: `tests/test_snapshots.py` with `tests/fixtures/aei_sample.csv`.

## 5. Example
SOC 43-3031 Bookkeeping, Accounting, and Auditing Clerks `usage_pct` GLOBAL 0.30 → 0.32 and MYS
0.28 → 0.30 (Apr → May 2026) → review `assistive.check_entries`, `assistive.match_transactions`,
`agentic.prepare_adjustments`. Accountants and Auditors 0.11 → 0.12 is below the noise floor → no
review. MYS overall automation share: 48.42 → 47.2.

## 6. Limits and honesty
Both periods come from one release (labelled historical replay). Usage share of Claude.ai
conversations is not adoption by companies and not proof of replacement. Indeed and HN signals are
not ingested yet.

## 7. Questions and answers
- *Does the data decide the roles?* No; it triggers a review, a human approves a new assumption.
- *Why Malaysia and global?* Malaysia is our context; global is the larger, more stable sample.
- *Is it real data?* Yes, AEI release 2026-06-26, CC-BY, cited in every snapshot.
- *Can it refresh?* `run_ingest()` is idempotent and can run on a schedule for new releases.

## 8. Design choices considered
Mapping usage directly to weights (would treat usage as replacement, which the data does not show);
O\*NET task-level signals (more granular but noisier per month; SOC level is easier to explain).
