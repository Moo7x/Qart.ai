# Qart.ai · Person A: Engine & Data (the "brain")

*You own: trend data, catalogues, skill model, recommender, scenarios, path planner, SDG mapping, HR aggregates, RunPod, evaluation, optimiser. Suggested for the team member with the data science/AI background.*
*Read first: `PROJECT_PLAN.md` and `team/00_SHARED_CONTRACT.md`. All times MYT.*

**You don't need any UI.** You test everything with fixture JSON and unit tests until merge point **M1**.

## Your increments (build the base first; every increment deployed and committed)
| Increment | Your part | Target | If it slips |
|---|---|---|---|
| **0 Base** | Minimal versions: evidence rules (A3 rules only) · `company_assumptions.json` v1 + requirement card (A2b) · recommender (A4) · simple path (greedy, before CP-SAT) · SDG map · **one** dated snapshot · endpoints for these | Thu midday | Hardcode fewer roles (3) and courses (15); keep the formulas |
| **1 Golden journey** | `next_case` targeting · path revision traced to events · "1 of 2 independent successes" messaging in `why` | M1, Thu 21:00 | Skip the provisional estimate; rules alone are enough |
| **2 Evidence → recompute** | Second snapshot + `diff()` + suggested assumption review + `PUT /api/assumptions` + recompute with `changed_since` | Fri midday | Use the Apr vs May 2026 periods from one AEI release |
| **3 Trust numbers** | Evaluation runner: acceptance counts, false alarms on clean cases, text-only baseline, final untouched set | Fri afternoon | Report fewer cases, honestly |
| **S1 RunPod spike (3 h)** | Embeddings + reranker endpoint for retrieval | Thu evening or Fri morning | Keep CPU BM25 retrieval; declare no GPU used; ask organisers whether RunPod proof is still required |
| **S3 Gate spike (4 h)** | One optimiser cycle → acceptance → proposal | Fri | Show a recorded, labelled run, or move it to the Upgrade Round |
| CP-SAT robust planner | Replace greedy with OR-Tools | Only after Increment 2 | Keep greedy; say so |

Drop rule: when a timebox ends without passing its test, stop, write one line in `docs/decision_log.md`, tell B, and move to the next increment.

---

## 0. Before you start (Day-0 session with B, Wed 21 Oct)
- [ ] Agree on the contract (`team/00_SHARED_CONTRACT.md`) and commit `schemas/examples/*.json`
- [ ] Create the repo from the organisers' template; branch `a/engine`; add `AGENTS.md` + `CLAUDE.md`
- [ ] Get API access for the chosen LLM provider; put the key in Replit Secrets and your local `.env`
- [ ] Create a RunPod account and **set a spending limit** (credit is US$25/team)
- [ ] Start `docs/DECLARATION_LOG.md` (library · version · licence · purpose) and add to it as you go

---

## 1. Phase 1 (Wed 21 evening → Thu 22): data + engine

### Task A1: Trend data → dated snapshots *(~4 h)*
Goal: at least **two dated snapshots** and a **diff**, so "output changes when trend data changes" is real.

> **v2 note:** snapshots hold **external evidence only (layer A)**. AI usage share is **not** proof of task replacement. Skill weights change through the **company assumptions** (Task A2b), never directly from the data.

1. **Anthropic Economic Index** (**data CC-BY, code MIT**; attribution required): Hugging Face `Anthropic/EconomicIndex`.
   - `release_2026_06_26/data/aei_claude_ai_2026-06-26.csv` (~220 MB, **don't commit it**: keep it in `data/raw/`, gitignored). It contains **April and May 2026** periods with `geo_id` = `GLOBAL`/`MYS`. That gives two dated periods from one release.
   - Filter: `geo_id in (GLOBAL, MYS)`, `category_name in (soc_occupation, onet)`, `metric_id = pct` (plus `collaboration_bucket_automation_pct` / `augmentation_pct` at country level).
   - Finance occupations to look for (SOC): 43-3031 Bookkeeping/Accounting/Auditing Clerks · 13-2011 Accountants & Auditors · 13-2051 Financial & Investment Analysts · 13-2031 Budget Analysts · 43-3051 Payroll Clerks · 43-3021 Billing & Posting Clerks · 13-1041 Compliance Officers · 15-2051 Data Scientists · 43-9111 Statistical Assistants. Keep the ones present.
   - Also `labor_market_impacts/job_exposure.csv` (observed exposure per SOC).
   - Optional third snapshot: an older release (`release_2026_03_24`). The schema differs, so only do it if time allows.
2. **Indeed Hiring Lab AI tracker** (free, cite): `github.com/hiring-lab/ai-tracker` → `AI_posting.csv`. Aggregate daily data to monthly. **9 countries, no Malaysia**, so label it "global AI-demand context".
3. **HN "Who is hiring"** (Algolia API): monthly counts for terms like `reconciliation`, `audit`, `FP&A`, `Excel`, `SQL`, `Python`, `agents`, `evals`, `data quality`, `automation`, **with the denominator** (total posts). Short terms are noisy, so hand-check a sample of 30 mentions and report precision. A working script exists in our research notes (`hn_test.py` pattern); rewrite it in the repo.
4. Write `src/engine/snapshots.py`: build `Snapshot` JSON (contract §4) per period → `data/snapshots/*.json`, each with `source`, `url`, `release_date`, `period`, `retrieved_at`, `signals`.
5. `diff(snap_a, snap_b)` → which signals changed, by how much, and which **assumptions are suggested for review** (`suggested_assumption_reviews`). The diff never changes weights by itself.

**Done when:** `data/snapshots/` has ≥2 dated snapshots, and `diff()` returns readable signal changes plus review suggestions.

### Task A2: Catalogues *(~3 h)*
- `catalogue/skills.json`: the shared skill IDs (contract §3), each with a name, a description, and a **type**: `execution` (doing the routine task, e.g. matching entries) or `oversight` (reviewing and judging AI output, e.g. `ai_output_review`, `escalation_judgment`). This classification drives the scenarios, so document why each skill gets its type.
- `catalogue/roles.json`: **4–6 internal finance roles**, each `based_on` real O\*NET 31.0 occupations (CC BY 4.0, cite with URL). Suggested:
  - `recon_associate` (current role; based on 43-3031)
  - `ai_finops_analyst` (13-2051 + 43-3031)
  - `controls_assurance_analyst` (13-2011 + 13-1041)
  - `fpa_analyst` (13-2031 / 13-2051)
  - `finance_data_quality_analyst` (15-2051 / 43-9111)
  - `process_automation_specialist` (15-1211, optional)
  - **Never invent a role without an O\*NET basis.**
- `catalogue/courses.json`: **~40 free or low-cost resources** with real URLs, hours, skills and retrieval date. Ideas: Kaggle Learn, Google/Microsoft free courses, Coursera audit-free courses, ACCA/AICPA free resources, ITU AI Skills Coalition, and HRD Corp-claimable listings (mark them `hrd_claimable`). Open every URL; **no invented courses**.
- `catalogue/sdg_map.json`: role → SDG targets and skill → SDG targets, each with a one-line rationale. Main **4.4**; 8.2 (productivity), 8.5 (decent work/redeployment), 5.5 / 10.2 only where genuinely relevant.
- **Each role lists its tasks** (taken from the O\*NET task statements of the occupations it's based on, cited). Each task is linked to the skills it uses, with a base importance.

### Task A2b: Company adoption assumptions, layer B *(~1.5 h)*
- `catalogue/company_assumptions.json` (contract "CompanyAssumptions"): for each scenario, **who does each workflow task** (`human` / `ai_drafts_human_reviews` / `ai`), plus the documented **shift rule** (e.g. 50%/80% of a task's execution-skill weight moves to oversight skills when AI takes the drafting).
- These are **explicit, labelled assumptions** (synthetic company). External evidence only **suggests a review**; HR (a synthetic account in the demo) accepts the change, which bumps the version.
- `requirement_card(role, scenario)`: tasks → allocation → resulting weights → "because" (assumption + the evidence that informed it). **This card is the bridge judges will inspect. Make it readable.**
- Test: changing one task's allocation changes the weights deterministically, and the card explains it.

### Task A3: Evidence rules + provisional estimate *(~3 h)*: `src/engine/skills.py`
**v2 priority:** the **user-facing** output is the rule-based state plus `why` plus `evidence_trail` (contract SkillState rules). Implement and test these first:
- Events flagged `companion_error` / `ambiguous_case` don't count.
- `demonstrated_independently` = ≥2 independent successes (≥1 check-in) on **different cases**, in **separate sessions**, with no independent failure since.
- Every state change produces a plain-language `why`.
- Unit tests for each transition.

Then the **internal, provisional** estimate (used only to order practice; **never shown as a percentage**). Bayesian knowledge tracing per skill, **where help lowers the weight of evidence**:
```
Parameters (declared assumptions, documented in code):
  prior P(L0)=0.20 · learn T=0.15 · slip S=0.10
  guess by help level G_h = [0.15, 0.30, 0.50, 0.75, 0.95]   # more help → a success says less
Update on success:  P(L|obs) = P(L)(1−S) / [P(L)(1−S) + (1−P(L))·G_h]
Update on failure:  P(L|obs) = P(L)·S   / [P(L)·S + (1−P(L))·(1−G_h)]
Then learning:      P(L) ← P(L|obs) + (1 − P(L|obs))·T
Check-in cases: help level 0 by definition.
This estimate does NOT decide the user-facing state (the rules above do). It only orders practice.
Reality gauge (UI) = self-rating shown next to the evidence state, not a subtraction of percentages.
```
- Keep self-confidence **separate**; it must not inflate the estimate.
- Unit tests: (a) success at h=0 raises the estimate more than success at h=3; (b) h=4 barely moves it.
- **Disclose in code, docs and UI:** "parameters are provisional assumptions; no learner data was available to fit them."
- The state shown to users comes from the **rules above**, not from estimate thresholds.

### Task A4: Scenarios + recommender *(~4 h)*: `src/engine/recommend.py` (v2 formula, same as PROJECT_PLAN §6)
```
Role skill weights w_{r,s,k}: from the role's tasks (base importance), then the company shift rule for
scenario s (layer B) moves execution weight to oversight skills for tasks the AI drafts or does. Renormalise.
coverage   = Σ_k w·credit(state_k) / Σ_k w      credit: demonstrated 1.0 · observed_with_help 0.5 · self_reported 0.2 · insufficient 0
confidence = share of weighted skills with ≥2 counted events
interest   ∈ [0,1]  overlap of interests with role tags
effort     = estimated hours to close gaps / (weekly_hours × 12), capped at 1     # PENALTY
score      = 0.55·coverage + 0.20·confidence + 0.10·interest − 0.15·effort
```
- The score is a **suitability indicator, not a probability**. Return every factor, the formula string, the gap list, the **requirement card** (Task A2b), sources, and `changed_since` (vs the previous assumptions version).
- **Sensitivity test:** vary the weights ±20% and check whether the top role changes. Report it.
- **Never** use demographic fields. A fairness test in Phase 2 proves it.

### Task A5: Next case + path planner *(~3 h)*
- `next_case(user, scenario)`: pick the practised skill with the highest `w·(1 − credit(state))`, breaking ties with the provisional estimate's uncertainty. Then pick an unseen case containing that skill (prefer `scenario_variant` matching the scenario). Return `because` (e.g. "you missed an unsupported adjustment in case_003").
- `src/engine/planner.py` with **OR-Tools CP-SAT**:
  - `x_i ∈ {0,1}` per resource (course or practice bundle).
  - Constraints: Σ hours·x ≤ weekly_hours × 6 weeks; prerequisites `x_j ≤ x_i`.
  - Gap per scenario: `g_{sc,k} ≥ 1 − credit(state_k) − Σ gain_{i,k}·x_i`, `g ≥ 0` (gain = 0.3 per covering resource; a declared assumption. **Coverage is not demonstrated skill until new evidence arrives.**)
  - Objective: **minimise max over scenarios of Σ r_{sc,s}·g_{sc,s}** (robust path).
  - Order the chosen items by prerequisites, then gap reduction per hour.
  - Greedy fallback if CP-SAT gives trouble.
- Output a `PathPlan` (contract). Test: a lower `weekly_hours` gives a different plan.

### Task A6: API + persistence + synthetic team *(~3 h)*
- `src/api_engine.py`: all **A-owned endpoints** in contract §5.
- `src/store.py`: SQLite or Replit Postgres. Seed on startup (Replit deployments may not keep local files across redeploys).
- `data/synthetic_team.json`: ~10 synthetic employees with event histories (labelled synthetic) for the HR aggregate summary. Include Aina (new hire) and Siti (at-risk clerk).
- `GET /api/hr/summary`: **aggregates only**. Per skill, counts of people in each state; groups smaller than 5 are suppressed; training demand per scenario. **No names, no "who should move where".** Individual recommendations exist only on the employee side (an employee may choose to share a portfolio; that's a later feature).
- `GET/PUT /api/assumptions` (layer B, versioned) and `POST /api/events/{id}/flag`.

**C1 checkpoint (Thu ~14:00):** show B the real JSON from `/api/recommendations` (incl. the requirement card), `/api/skills` (state + why + trail) and `/api/path`. Confirm B's `Event` JSON is accepted by `POST /api/events`.

**v2 priority order if time is short:** evidence rules (A3) → requirement card + assumptions (A2b) → recommender (A4) → path (A5) → next case (A5) → snapshots diff (A1, needed for golden-journey step 6 by M2) → HR summary. **The golden journey (contract §6) is the target, not the full endpoint list.**

### ⛔ Stop and merge, M1 (Thu ~21:00)
Stop feature work when:
- (a) it's 21:00, **or**
- (b) your endpoints all return contract-valid JSON with real computation, **or**
- (c) you're blocked >1 h on something needing B.

Then merge `a/engine` → `main` with B and run the **golden journey test, steps 1–5** (contract §6) on the Replit URL. **Don't start the spikes until it passes.** Steps 6–7 must pass by M2.

---

## 2. Phase 2 (Fri 23): proof and depth

### Task A7: RunPod retrieval *(~3 h)*
- Deploy `runpod/handler.py` (from the template) as a **Serverless endpoint**:
  - **BAAI/bge-small-en-v1.5** (MIT) for embeddings
  - **BAAI/bge-reranker-v2-m3** (Apache-2.0) for reranking
  - Min workers 0, max 1, short idle timeout.
- Use it for (a) the course and role-requirement search behind the pathway, (b) matching free-text intake skills to skill IDs, (c) retrieving playbook passages the companion cites.
- Pipeline: BM25 (`rank_bm25`) + embeddings → reciprocal-rank fusion → rerank → **"no source → no claim"**.
- Mini benchmark: 15 labelled queries → **recall@5 BM25 vs hybrid+rerank**.
- **Screenshot the RunPod dashboard** (endpoint URL, GPU type, runtime) → `submission/` + declaration.

### Task A8: Evaluation runner *(~3 h)*: `eval/`
- **Independence beats count.** The **acceptance set** = B's **independently authored acceptance cases** (different error mechanisms and case structures, not variants of practice cases) + clean cases. It lives in `eval/acceptance/` with fixed criteria in `eval/acceptance_criteria.py` (hashed), and is never readable by the optimiser.
- `eval/variants.py`: perturb the practice cases (amounts, names, dates; same ground truth) → variants for the **optimisation set** and for robustness checks only. **Variants never go into the acceptance set.**
- Run each candidate against the acceptance set **once**. If you catch yourself changing things because of acceptance results, that set has become development data: move it to optimisation and use the **final untouched set** (2–4 cases B keeps aside) for the reported numbers.
- Run `auto_diagnose()` (B's function) on all variants. Report:
  - Root-cause accuracy and decision accuracy.
  - **False-alarm rate on clean cases.**
  - Baseline: the same LLM given the raw tables without tools.
- Also report: time from profile to path, the weight-sensitivity result, and the **fairness test** (synthetic twins differing only in gender/age fields, which must give identical rankings).
- Write `eval/RESULTS.md` with counts, not just percentages. **These numbers go in the PRD and pitch. Never round them up.**

### Task A9: Self-improvement optimiser *(~3 h)*
- **Editable scope: the playbook only.** Hint sequencing, retrieval, grader, evidence rules, acceptance cases and criteria are all out of bounds.
- Collect failure traces from the **optimisation set** → LLM proposes an edit to `src/companion/playbooks/playbook_v1.md` → evaluate on the optimisation set → if better, run the **fixed acceptance tests** (+ false alarms on clean cases, invalid citations) and regressions against the **current playbook as baseline** → write an `OptimizerProposal` (contract) with status `pending`. Report **counts**, not broad claims.
- Use **GEPA** (MIT) if it integrates quickly, otherwise a simple reflective loop.
- `POST /api/optimizer/proposals/{id}/decision` (senior) → approve activates `playbook_v2`, reject keeps v1; versioned, with rollback.
- **The optimiser may never edit the evaluator, the acceptance set or its criteria, or the approval rule.** If there's no gain, show the rejection. That's a valid demo.

**C2 (Fri ~14:00):** agree with B what's cut. **M2 (Fri ~22:00):** full demo rehearsal together.

---

## 3. Sat 24: submission (your parts)
- [ ] `submission/SDC2026_TeamName_TechDeclaration.pdf`: every API, model, dataset (with licence), library, AI dev tool (Claude Code/Codex, "major" extent), sponsor resources; **Replit proof**; **RunPod screenshot**; data handling ("synthetic only"); limitations (from `eval/RESULTS.md`)
- [ ] PRD technical sections (3.1 tech stack + block diagram; Impact Framework numbers and citations)
- [ ] README: fill in the template's sections ("How we use Replit / RunPod", tech stack, how to run, team)
- [ ] Repo **public**, committee collaborators added, no secrets (run a secret scan), LICENSE present
- [ ] Submit on sdchack.my by ~22:00. **Then stop pushing: the repo is frozen after the deadline.**

---

## 4. Guidance for your coding agent (Claude Code / Codex)
**Start every session with:**
> "Read AGENTS.md, PROJECT_PLAN.md and team/00_SHARED_CONTRACT.md. You are helping Person A, who owns src/engine, src/api_engine.py, src/store.py, catalogue/, data/, eval/, runpod/. Don't edit other folders. Follow the JSON contract exactly. Prefer simple, explainable code with the formulas documented in comments, and add unit tests."

**Good task prompts (one per session, small):**
1. "Write `src/engine/snapshots.py` that reads the filtered AEI CSV in data/processed/ and builds two Snapshot JSON files (April and May 2026, GLOBAL+MYS) following schemas/examples/snapshot.json, plus a `diff()` with human-readable 'because' strings. Add tests."
2. "Implement the evidence-state rules from team/00_SHARED_CONTRACT.md (SkillState rules) with a `why` string and evidence trail, ignoring flagged events, plus a unit test per transition. Then add the provisional help-weighted BKT estimate from Task A3 as an internal field."
3. "Implement company_assumptions.json loading and `requirement_card(role, scenario)` per Task A2b, then `recommend()` with the v2 formula per Task A4. Return every factor, the formula string and the card. Add a ±20% weight sensitivity test."
4. "Implement the robust CP-SAT path planner per Task A5 with a greedy fallback, and a test that a smaller weekly budget changes the plan."
5. "Create FastAPI routes for the A-owned endpoints in contract §5, with Pydantic models matching schemas/examples."

**Review rules for yourself:**
- Read every diff before committing. You must be able to explain every formula to a judge (AI policy rule 4).
- Don't let the agent "fill in" courses, roles or statistics. You verify every URL and number.
- Log each library, model and dataset in `docs/DECLARATION_LOG.md` the moment it's added.
- Commit small and often on `a/engine`.

## 5. Things that will bite you (and how to avoid them)
- **Big files:** never commit the 220 MB AEI CSV. Commit the processed snapshots only.
- **Replit:** deploy early (Thu). Check that the deployment URL stays up through judging (25–28 Oct), and **don't redeploy after the deadline**.
- **Costs:** cap the LLM spend and the RunPod workers. Cache LLM results for the demo personas (a labelled demo mode) so the live demo doesn't depend on latency.
- **Honesty:** label historical replays as replays, label synthetic data as synthetic, and report small-sample numbers as counts.
- **Explainability for both of you:** at M1 and M2, give B a 15-minute walkthrough of the engine. Judges can question either of you about any part.
