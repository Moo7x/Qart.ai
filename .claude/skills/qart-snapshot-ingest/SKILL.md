---
name: qart-snapshot-ingest
description: Ingest a dated public trend source (Anthropic Economic Index, Indeed Hiring Lab AI tracker, HN "Who is hiring" counts) into a Qart.ai Snapshot, compute the diff against the previous snapshot, and produce suggested assumption reviews. Use when building or refreshing the signal layer (Person A).
---

# Qart.ai snapshot ingestion (layer A: external evidence)

## Rules
- Snapshots hold **external evidence only**. AI usage share is **not** proof of task replacement. Never change role skill weights directly from a snapshot; produce `suggested_assumption_reviews` for HR to approve (layer B).
- Every snapshot records `source`, `url`, `release_date`, `period`, `geo`, `retrieved_at`, and the licence (AEI data: CC-BY, attribution required; Indeed: cite Hiring Lab; HN: public API).
- Never commit raw large files (the AEI CSV is ~220 MB). Keep them in `data/raw/` (gitignored) and commit only `data/processed/` and `data/snapshots/`.

## Steps
1. **AEI:** load `release_2026_06_26/data/aei_claude_ai_2026-06-26.csv`. Filter `geo_id in (GLOBAL, MYS)`, `category_name in (soc_occupation, onet)`, metric `pct`, plus country-level automation/augmentation shares. Keep finance-related SOC codes (43-3031, 13-2011, 13-2051, 13-2031, 43-3051, 43-3021, 13-1041, 15-2051, 43-9111) present in the data. Build one snapshot per monthly period (April and May 2026).
2. **Indeed AI tracker (optional context):** `AI_posting.csv` → monthly mean per country. Label "9 countries, not Malaysia".
3. **HN hiring (optional):** monthly mention counts with the total-post denominator. Hand-check a sample of 30 mentions and record precision.
4. Write `data/snapshots/<id>.json` per the contract Snapshot example.
5. `diff(previous, new)`: list signals that changed (value before → after, period), then map them to `suggested_assumption_reviews` using the documented mapping in `catalogue/company_assumptions.json` (e.g. a rise in AI usage on bookkeeping tasks → review "assistive.match_transactions").
6. Print a short human-readable diff for the HR banner, labelled "historical data replay" when replaying past releases.
7. Log the source in `docs/DECLARATION_LOG.md` (use the qart-declaration-log skill).
