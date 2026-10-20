# Person A progress (engine & data), 2026-10-21

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
