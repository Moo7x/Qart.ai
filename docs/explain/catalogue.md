# Catalogues (`catalogue/`, `src/engine/catalogue.py`)

## 1. What it does
Static reference data the engine reasons over: the 16 skills, 4 internal roles based on real O\*NET
occupations, 16 free learning resources, the SDG map, and version 1 of the company's AI-adoption
assumptions. `load_catalogue()` reads and validates all of it into typed objects.

## 2. Why it exists
The brief forbids invented jobs, courses or statistics (AGENTS.md). Every role points to O\*NET 31.0
pages (CC BY 4.0) and copies their task statements word for word; every course URL was opened on
2026-10-21. Must-haves served: explainable role score (roles + tasks), learning path (courses), SDG
tags (sdg_map).

## 3. How it works
- **skills.json**: each skill is `execution` (doing routine work AI can draft, e.g. matching) or
  `oversight` (judging work, e.g. `ai_output_review`). The type drives the shift rule. Each has a
  `type_reason`. *Declared* classification.
- **roles.json**: role → `based_on` O\*NET codes → `tasks` (verbatim task statements) → each task
  lists the skills it uses and the company `workflow_task` it maps to. `base_weight` (0–1 importance)
  is a *declared* team judgment.
- **company_assumptions.json** (layer B, *assumption*): who does each workflow task per scenario
  (`human` / `ai_drafts_human_reviews` / `ai`), the shift rule (50% assistive / 80% agentic of the
  execution weight moves to oversight skills), and `review_triggers` (which external signal should make
  HR review which assumption). Later versions are stored by the API when HR approves a change.
- **courses.json** (26 items, incl. 6 Microsoft Learn modules, AccountingCoach on bank
  reconciliation, the IFRS IAS 21 summary and IFAC's paper on professional skepticism): `verified=true` = page loaded, title and cost checked. `cost` says
  "free" only where the provider states it, and `cost_source` records where (Kaggle "no-cost
  courses", Microsoft Learn FAQ "training is free", OpenLearn "Free course"…). SQLBolt and the
  Microsoft Support Excel page show no price but do not say free, so they are labelled "no price
  shown (not stated as free)". The COSO Coursera course is "paid (Coursera)" (checked by Person A
  on 2026-10-21); the free COSO *Internal Control — Integrated Framework: Executive Summary* PDF on
  coso.org is the free alternative (linked only; © COSO). `hours_source` marks estimates.
- **sdg_map.json**: 4.4 (main), 8.2, 8.5 with one-line rationales for every role and skill.

**One skill vocabulary (QART_NEXT_STEPS §2).** `skills.json` lists every skill the app uses:
practice skills, role skills and market skills. `evidence_tracked` marks the 16 whose evidence
state is kept (cases, My skills, HR). `trend_tracked` marks the 20 with Hacker News patterns for
the Skills Radar. `learn_hours` gives team estimates (ASSUMPTION) for none → "use sometimes" →
"confident". `tests/test_skill_vocabulary.py` fails on any unknown skill id in roles, courses,
the SDG map or cases.

## 4. Where in the code
`src/engine/catalogue.py::load_catalogue`, `default_catalogue` (cached). Integrity tests:
`tests/test_catalogue.py` (no dangling ids, every role cited, every unverified course explained).

## 5. Example
`ai_finops_analyst` is based on 13-2051.00 and 43-3031.00. Its task "Reconcile records of bank
transactions." (43-3031.00) maps to `match_transactions` and uses `recon_to_source`,
`duplicate_detection`, `cutoff_timing`. Under *agentic* that task is done by `ai`, so 80% of those
execution weights move to the role's oversight skills.

## 6. Limits and honesty
Base weights and task-skill links are our judgment, not O\*NET importance ratings. Kaggle and some
Microsoft hours are estimates (marked). None of the courses are HRD Corp listings yet.

## 7. Questions and answers
- *Did you invent these roles?* No: each is an internal title built on cited O\*NET occupations and
  their task statements.
- *Are the courses real?* Yes, every URL was opened on 2026-10-21; unconfirmed items are flagged.
- *Why these weights?* Declared design choices, shown on the requirement card and tested for ±20%
  sensitivity.
- *Who decides how much work AI does?* The company (HR), in layer B. Data only suggests a review.

## 8. Design choices considered
Using O\*NET importance ratings directly (more lookups, little gain for 4 roles); scraping a course
API (no reliable free API for all providers; manual verification is more honest at this size).
