# Person A progress (engine & data), 2026-10-21

## Run 2 status (resume here)
Items from the second brief, done in order; each line is updated when an item is committed.
- [x] 1 Role outlook: `role_outlook()` in `src/engine/requirements.py`, `outlook` on each
  recommended role and the requirement card, `changed_since.outlook_changes`; thresholds
  `OUTLOOK_*` in `params.py`. Tests in `tests/test_requirements.py`, `tests/test_api.py`.
- [x] 2 Readable ranking: `fit`, `time_to_ready`, `close_match` on each recommended role;
  displayed `score` clamped at 0 (ordering uses the unclamped formula); `score_note` explains the
  penalty. Params `SCORE_DISPLAY_FLOOR`, `CLOSE_MATCH_THRESHOLD`. Tests in `tests/test_recommend.py`.
- [x] 3 Case index reader: `load_case_index()` reads B's `cases/index.json` (`practised_skills`)
  and falls back to `data/case_index.json`; fixture `tests/fixtures/cases_index.json`. Q4 updated
  (skills-on-Case proposal withdrawn). `cases/` was not created.
- [x] 4 Course costs: planner uses any verified course (free or paid); every step shows its cost;
  cheaper course covering the same gap wins (`prefer_cheaper`, tie-break in greedy; params
  `COST_TIER_*`). COSO course_16 = "paid (Coursera)", verified; new free course_17 = COSO's official
  Executive Summary PDF. SQLBolt and MS Support relabelled "no price shown (not stated as free)".
  Every course has `cost_source`. Tests: `tests/test_course_costs.py`.
  Coverage of role skills by verified courses (free / paid-or-unstated):
  - Only paid/unstated besides a free one: controls_design (free 17, paid 16), sql_basics (free 04,
    unstated 06), spreadsheet_modelling (free 02, unstated 13).
  - **No course at all** (covered only by in-app practice cases): duplicate_detection,
    escalation_judgment, fx_conversion, transposition_check, unsupported_adjustment. I did not add
    courses for them (none verified yet); candidates need your approval.
  - All other role skills have at least one verified free course.
- [x] 5 Evaluation scaffold: `eval/runner.py` (`python -m eval.runner`) grades B's
  `auto_diagnose` (stub until `src/companion/auto.py` exists) and a text-only baseline (stub; no LLM
  called) with fixed criteria in `eval/acceptance_criteria.py` (sha256 shown in RESULTS); writes the
  "companion-evaluation" section of `eval/RESULTS.md` ("Not run" while `eval/acceptance/` is empty).
  Tests: `tests/test_eval_runner.py`. Type checks now run as `mypy src eval`.
- [x] 6 Q12 added to `docs/CONTRACT_QUESTIONS.md`; explain docs updated (requirements, recommend,
  planner, catalogue, next_case, ARCHITECTURE) and new `docs/explain/evaluation.md`.
- [x] 7 Postgres backend: `src/store.py` uses Postgres (psycopg 3) when `DATABASE_URL` is set,
  SQLite otherwise; same tables/behaviour; seeding guarded by an advisory lock. Tests run on SQLite
  (`tests/test_store_backend.py` covers selection and the placeholder adapter). **Not yet run
  against a real Postgres**: verify on Replit (see manual steps).
- [x] 8 Retrieval preparation: `src/retrieval/` (Retriever interface, BM25 + filters, RRF hybrid,
  RunPod BGE-M3/bge-reranker interfaces), corpus of verified courses + O*NET 31.0 tasks/DWAs
  (`data/processed/onet_tasks_dwas.json`), 129 Microsoft Learn candidates (not used by the
  planner), BM25 recall@5 = 0.78 (21/28) in `eval/RESULTS.md`. Not wired into the planner or API.

Branch `a/engine`, not pushed. All checks green at the last commit:
`ruff format --check .` ✔ · `ruff check .` ✔ · `mypy src` (strict) ✔ · `pytest`: **104 passed**.

## What's done, per step
| Step | Done | Where |
|---|---|---|
| 0 Setup | Python 3.12 venv; `pyproject.toml` (ruff E,F,I,B,UP,SIM,N @100, mypy strict + pydantic plugin, pytest); pinned `requirements.txt`; `.replit` runs uvicorn on 8000; `.env.example` names only; contract examples in `schemas/examples/` + models in `src/contract.py`; every weight/threshold in `src/engine/params.py` | `src/main.py` mounts the engine router, B's router once `src/api_companion.py` exists, and `web/dist` once built |
| 1 Catalogues | 16 skills with execution/oversight type + reason; 4 roles on O\*NET 31.0 (43-3031, 13-2051, 13-2011, 13-1041, 13-2031) with verbatim task statements; company assumptions v1 (allocation per scenario, shift rule, review triggers); SDG map (4.4 main, 8.2, 8.5); **16** free courses, all URLs opened 2026-10-21 (COSO course `verified: false`) | `catalogue/` |
| 2 Evidence rules | Contract states, flags not counted, `why` with "1 of 2 independent successes", evidence trail, `next_to_confirm`, internal help-weighted BKT estimate | `src/engine/skills.py` |
| 3 Card + recommender | `requirement_card()` (tasks → allocation → weights → because); v2 formula with every factor, formula string, gap, sources, `changed_since`; ±20 % sensitivity report | `src/engine/requirements.py`, `recommend.py`, `eval/SENSITIVITY.md` |
| 4 Path + next case | Greedy robust planner (budget, prerequisites, worst-case gap over both scenarios), confirmation check-in replaces the learning module; `next_case` with `because`; **CP-SAT version** behind the same interface | `planner.py`, `planner_cpsat.py`, `next_case.py`, `data/case_index.json` |
| 5 Snapshots | AEI release_2026_06_26 claude_ai CSV → snapshots for 2026-04 and 2026-05 (GLOBAL + MYS, finance SOC codes); `diff()` → suggested assumption reviews; reusable ingest | `src/engine/snapshots.py`, `ingest.py`, `data/snapshots/` |
| 6 API + store | All A endpoints of contract §5 + `/api/ingest/run`, `/api/demo/reset`, `/api/profile/{id}`, `/api/health`; SQLite store with change log; 12 synthetic employees (Aina, Siti, a 3-person team to test HR suppression) | `src/api_engine.py`, `src/store.py`, `src/engine/hr.py`, `data/synthetic_team.json` |
| 7 Final checks | Contract check: live outputs contain every example field, contract example event accepted, formula string fixed, no percentages in `why`, HR has no names, secrets scan clean; declaration and decision logs updated; `docs/explain/` covers every module + ARCHITECTURE | `tests/test_contract_outputs.py`, `docs/` |

Golden journey (contract §6) as covered by tests: steps 1–6 pass through the API in
`tests/test_api.py` (step 7 needs B's grader and cases).

## How to run
```bash
py -3.12 -m venv .venv
```
```bash
.venv/Scripts/python -m pip install -r requirements.txt
```
```bash
.venv/Scripts/uvicorn src.main:app --host 0.0.0.0 --port 8000
```
Then open http://localhost:8000/docs. Checks:
```bash
.venv/Scripts/ruff format . && .venv/Scripts/ruff check . && .venv/Scripts/mypy src && .venv/Scripts/pytest
```
Rebuild snapshots (downloads ~220 MB into gitignored `data/raw/` if missing):
```bash
.venv/Scripts/python -m src.engine.ingest --retrieved-at 2026-10-21
```
Sensitivity report: `python -m eval.sensitivity`. Reset the demo: `POST /api/demo/reset`.
On Replit, Linux paths are `.venv/bin/...`; the `.replit` run command is already set.

## Results worth knowing
- Aina after case_003 → case_006 → checkin_001: `unsupported_adjustment` = observed_with_help,
  "1 of 2 independent successes (checkin_001)…", next to confirm `checkin_002 (later session)`.
- Next case: case_006 → checkin_001 → case_009 (the transposition miss from case_003 moves up).
- Path (ai_finops_analyst, 4 h/week): the adjustments bundle becomes one 0.5 h confirmation
  check-in; at 1 h/week the plan is shorter. CP-SAT is never worse than greedy (≤ 0.02 better).
- AEI May vs April 2026: SOC 43-3031 usage 0.30 → 0.32 (GLOBAL), 0.28 → 0.30 (MYS) → reviews
  `assistive.check_entries`, `assistive.match_transactions`, `agentic.prepare_adjustments`.
  Approving v2 (assistive check_entries → AI drafts) changes recon_associate's card and score
  (0.07 → 0.08); **no rank flips for Aina** with the contract shift rule (honest result).
- Sensitivity: the post-journey agentic top role is stable under ±20 %; intake rankings are near
  ties and flip on interest/effort (see `eval/SENSITIVITY.md`). Scores are small (some slightly
  negative) because effort is a real penalty at 4 h/week.

## What's left (not done)
- Indeed Hiring Lab and HN "Who is hiring" signals (Task A1 items 2–3); optional third AEI release.
- Evaluation runner (A8), RunPod retrieval spike (A7), optimiser (A9): the proposals endpoint is a
  stub that returns `[]` and never invents results.
- Replace `data/case_index.json` with B's case metadata once agreed (Q4).
- More courses (target was ~40; 16 verified now), HRD Corp-claimable listings (none yet).

## Open questions
See [CONTRACT_QUESTIONS.md](CONTRACT_QUESTIONS.md): Q1 `outcome: "failure"`, Q2 optional extra
fields, Q3 state edge cases, Q4 case metadata without ground_truth, Q5 `case_007` clash, Q6–Q11
response shapes (profile, flag, diff, HR summary, PUT assumptions).

## What you must do manually
1. Read the diffs (29 new commits on `a/engine`) and agree Q1–Q11 with Person B at C1.
2. Confirm the COSO course's free access (or drop it), and spot-check Kaggle/Microsoft course hours
   marked as estimates in `catalogue/courses.json`.
3. Push `a/engine` when ready (`git push origin a/engine`); I did not push.
4. On Replit: install requirements, set `QART_DB_PATH` if you want the DB elsewhere, and run once to
   seed. The raw AEI CSV is not needed there (snapshots are committed).
5. Tell Person B: events must use `help_level 0` for check-ins (422 otherwise), and the default
   practice scenario for `/api/next-case` is `assistive`.

## Run 2 end-of-run report (2026-10-21)

### a) What was built, and results
14 commits on `a/engine` (not pushed): items 1–8 above. Checks at the last commit:
`ruff format --check .` ✔ · `ruff check .` ✔ · `mypy src eval` (strict) ✔ · `pytest`: **147 passed**
(was 104; all earlier tests, incl. the golden-journey API tests, still pass; the only edited
existing test is the score assertion, which now expects the clamp asked for in item 2).
Results worth quoting: role outlook recon_associate 0.45 stable (assistive) / 0.79 being
transformed (agentic), assistive → being transformed after the v2 approval; close_match flags
exactly the rankings the ±20% check found unstable; BM25 recall@5 0.78 (21/28, synthetic set);
companion evaluation "not run" (no acceptance cases, auto_diagnose missing).

### b) Blocked or unverified, with options
1. **Postgres path not run against a real database** (no server here).
   Options: (i) *recommended*: on Replit, enable the built-in Postgres (sets `DATABASE_URL`), run the
   app once, then call `POST /api/demo/reset` and the golden-journey test; (ii) run a local Postgres
   in Docker and I add an opt-in `pytest -m postgres` test (needs Docker; more setup); (iii) deploy
   on SQLite (works, but Replit may lose the file and multiple instances won't share data).
2. **Five practised skills have no course** (duplicate_detection, escalation_judgment,
   fx_conversion, transposition_check, unsupported_adjustment); they are covered by in-app
   practice. Options: (i) keep in-app practice only (*recommended*: these are our case skills);
   (ii) I search for verified free resources per skill and list them as candidates for your
   approval; (iii) approve relevant Microsoft Learn candidates (none target these skills directly).
3. **Microsoft Learn Catalog API is marked for deprecation** (Microsoft says it works through June
   2026 and recommends the Learn Platform API; it still answered on 2026-10-21). Options: (i) keep
   it while it answers (*current*); (ii) switch `mslearn.py` to the Learn Platform API after you
   approve that source (see "New sources" below).
No scope was cut; nothing from PROJECT_PLAN or the contract was removed or simplified.

### c) What you must do yourself
1. Review the 14 commits, then push `a/engine`.
2. Approve or reject Q1–Q12 with Person B (`docs/CONTRACT_QUESTIONS.md`), especially Q4 (index
   format), Q12 (new optional fields + clamped score).
3. On Replit: install `requirements.txt` (now includes `psycopg[binary]`), turn on Replit Postgres,
   check the app starts and seeds (see b1). Never put the URL in code; it lives in Replit Secrets.
4. Spot-check estimated course hours (marked in `hours_source`) and the 129 Microsoft Learn
   candidates; tell me which to approve into `courses.json`.
5. Decide on the new sources below (I did not add them).

### d) What unblocks my next work, and what to ask Person B
| Checkpoint | Ask Person B for | Unblocks |
|---|---|---|
| C1 (Thu 22 Oct ~14:00) | Agree Q1–Q12; event JSON from the companion (check-ins with help 0; outcome `failure` OK?); UI uses `fit`, `time_to_ready`, `close_match`, `outlook` and never shows `provisional_estimate` | API contract freeze |
| C1 | `cases/index.json` in the Q4 format (id, mode, difficulty, scenario_variant, practised_skills), with ids matching the golden journey | next-case and path on real cases (reader already done) |
| M1 (Thu 22 Oct ~21:00) | `src/companion/auto.py::auto_diagnose(case, playbook_path)` and `grader.py::grade` per contract §5; `src/api_companion.py` exposing `router` | evaluation runner (no code change needed), golden journey steps 1–5 end to end |
| C2 (Fri 23 Oct ~14:00) | Independently authored acceptance cases + clean cases in `eval/acceptance/`, plus a final untouched set kept aside; path of `playbook_v1.md` | real acceptance counts in `eval/RESULTS.md` |
| C2 | Who owns the provider-agnostic LLM client (OpenAI via `LLM_API_KEY`) | text-only baseline and the optimiser (A9) |
| M2 (Fri 23 Oct ~22:00) | UI for the snapshot diff → HR approval flow (`POST /api/ingest/run`, `PUT /api/assumptions`) | golden journey step 6 in the UI |

### e) Merge to main
**Not due now.** The next merge is at **M1 (Thu 22 Oct ~21:00)**, once B's branch is pushed and
golden-journey steps 1–5 can run end to end (`origin/main` today only has a README update; there
is no `b/app` on the remote yet). Steps at M1:
1. Both push their branches (`git push origin a/engine`, B pushes `b/app`).
2. On GitHub open a pull request `a/engine` → `main`; merge with **"Create a merge commit"**
   (no squash, no rebase). Merge **A first**.
3. Then open and merge B's pull request `b/app` → `main` the same way, resolving any conflict in
   the shared files (`src/main.py`, `schemas/`) together.
4. Each person merges `main` back into their branch (`git checkout a/engine` then
   `git merge origin/main`, after `git fetch`), runs the checks, and pushes.
5. Run the golden-journey test on the Replit URL.

### New sources found (not added; waiting for your approval)
- **O*NET 31.0 `emerging_tasks.csv`** (same CC BY 4.0 database): new tasks reported for
  occupations; could inform the role outlook with evidence rather than assumptions alone.
- **O*NET 31.0 `task_ratings.csv`**: task importance ratings; could replace our declared role
  base weights with sourced ones.
- **COSO "GenAI" paper (Feb 2026)**, linked on https://www.coso.org/guidance-on-ic: internal control
  over generative AI; a strong free resource for `controls_design` and `ai_output_review` if free.
- **Microsoft Learn Platform API** (successor to the Catalog API): needed if the old endpoint stops.
