# Qart.ai Phase 2 (finalist) plan

Scope and work split for the finalist round. It extends `docs/PLAN.md`; where the two differ, this
file wins. Every coding agent reads `AGENTS.md`, then this file, then only the sections of
`docs/PLAN.md` its task touches.

Two branches are cut from `main` after Stage 0:

| Branch | Owner | Theme |
|---|---|---|
| `p2-ai-experience` | Moo7x (A) | Evidence, forecasting, search, agents, Overview and trends screens, status, privacy, load test |
| `p2-scoring-pathway` | Meiirman (B) | Skill levels, fit score, learning-gain model, pathway, SDG mapping, personas, onboarding, badges |

An agent works only inside its branch's files (§5). Anything outside them is a request to the other
owner, written in the commit body or raised in chat, never an edit.

---

## 1. Decisions for Phase 2

What changed against `docs/PLAN.md` and `AGENTS.md`, decided by the team for the finalist round:

1. **Users:** working adults, juniors / fresh graduates and students. **The HR / L&D view is out of
   scope.** "Company" aggregates are dropped with it.
2. **Levels are described, not numbered.** The proficiency scale becomes 0–5, aligned with SFIA's
   lower five levels: 0 none · 1 novice · 2 aware · 3 working · 4 proficient · 5 expert. Every skill
   has one "I can…" sentence per level (§4 C1). Three rules: done, not studied (level 3 and above
   need work experience; a course alone reaches level 2 at most); pick the highest true sentence;
   link a CV line where possible.
3. **The progress-check agent may assess.** A finance-practitioner agent asks a person about the work
   they did, judges it against the level descriptions and proposes a level. The person accepts or
   declines; an accepted result is stored as a claim with source `agent_check`. The app still never
   tutors or hints at answers, and never makes hiring, promotion or dismissal decisions.
4. **Study and practice are separate.** Study time moves a skill to level 2 at most; level 3 needs a
   practice task at work. Plans show two fit ranges: after study and after study and practice.
   Course durations are labelled by what they measure (reading estimate, guided hours, practice
   estimate).
5. **Fit is shown as a range and a band**, with its components and what would raise it, in a large,
   clickable panel, not small print.
6. **The plan adapts to the person.** AI basics are skipped when the CV shows AI or automation
   experience; course level follows the claimed level; advanced people get practice and project
   steps instead of beginner courses.
7. **SDG contribution is a heatmap** (skills or steps × SDG targets, cells = planned hours, a click
   opens the one-line reason and source) plus a total per target.
8. **Forecasting is part of the product.** The brief asks to *predict* emerging and declining skills
   and jobs, so trends get forecasts with backtests against simple baselines, labelled estimates.
9. **One visible agent workflow is attempted:** a resource scout that finds the exact part of a video
   or article that teaches a gap, shown in an in-app agent window. If the visual part fails, the same
   result is reported in a step log.
10. **Models:** `gpt-4o-mini` stays for CV extraction and explanations. Agents use `AGENT_MODEL`
    (default `gpt-4.1-mini`: a mid-tier model, not the most expensive). Both are named on screen
    and in the declaration.
11. **No login.** The profile stays an anonymous 128-bit id in the browser. Phase 2 adds a resume
    code, data export and delete (§7 A8).
12. **Later, not now:** the funding / training-request step (HRD Corp, PERKESO, MyMahir); weights
    from job-post RCA; Chinese interface; route options; auto-generated video.

---

## 2. Branches and merging

1. **Stage 0** (§3) is committed on `main` first. Both branches start from that commit:
   `git switch -c p2-ai-experience` and `git switch -c p2-scoring-pathway`.
2. Never merge one feature branch into the other directly. Never rebase, squash or force-push.
3. **Merge points.** There are two: M1 after Stage 1 of both branches, M2 at the end. At each one:
   1. B goes first: `git switch main` → `git merge --no-ff p2-scoring-pathway` → all checks → the
      human pushes.
   2. A takes `main` in: `git switch p2-ai-experience` → `git merge main` → fix → all checks.
   3. A merges in: `git switch main` → `git merge --no-ff p2-ai-experience` → all checks → push.
   4. B takes `main` in: `git switch p2-scoring-pathway` → `git merge main`.
   B goes first because the level scale and the score fields change data that A only reads.
4. **Checks before every commit and merge:** `ruff format . && ruff check . && mypy src && pytest -q`.
   In `web/`: `npm run lint && npm run build`. A merge also needs the persona journey test (§7 B6).
5. **Conflicts in docs** (`docs/decision_log.md`, `docs/DECLARATION_LOG.md`, `docs/explain/*`):
   keep both entries. **Conflicts in code** go back to the owner of that file (§5).
6. Commits stay small (`area: what changed`), with no AI attribution lines. Build steadily through
   the 48-hour sprint: the final report (§3.2) asks what was built in it.

---

## 3. Stage 0: shared contracts on `main` (before branching)

These edits touch files that both branches would otherwise change. Done once, on `main`.

| # | Change | Files |
|---|---|---|
| S0.1 | This plan; updated `AGENTS.md` and the `docs/PLAN.md` header | docs |
| S0.2 | **One LLM client.** Add `src/llm.py`: `complete(settings, messages, schema, *, model=None, purpose: str) -> str`. It wraps the OpenAI call (time budget, JSON schema) and records usage. Move the three existing call sites (`intake/extract.py`, `match/explain.py`, `goal/posting.py`) onto it. Behaviour must not change, and tests stay green. | `src/llm.py`, 3 call sites |
| S0.3 | **Usage counter.** Add `src/usage.py` with a `usage_event` table: `id, at, purpose, engine (openai/runpod/fallback), model, tokens_in, tokens_out, seconds, ok`. Add `record(...)`. Wire `src/llm.py` and `src/runpod_jobs.py` to it, and register the table in `src/app.py`. This is the measured input for cost per user (Section 4 of the report). | `src/usage.py`, `src/runpod_jobs.py`, `src/app.py` |
| S0.4 | **Settings.** Add `agent_model` (env `AGENT_MODEL`, default `gpt-4.1-mini`) to `src/config.py`; add `AGENT_MODEL=` to `.env.example`. | `src/config.py`, `.env.example` |
| S0.5 | **Claim sources.** `SkillClaim.source` gains `"agent_check"`. Add optional fields `checked_at: datetime \| None` and `model: str = ""`. Old rows still load. | `src/journey/store.py` |
| S0.6 | **Course fields.** `Course` gains optional `time_basis: Literal["reading_estimate","guided_hours","stated"] = "reading_estimate"`, `hands_on: bool = False`, `checked: str = ""` and `verified: bool = True`. The pack loads every `courses*.yaml` in the pack folder (current file first), and the same for `resources*.yaml`. | `src/pack.py`, `src/resources.py` |
| S0.7 | **Stub routers**, registered once in `src/app.py`, each an empty `APIRouter` with a module docstring naming its owner. A: `src/api/agents.py`, `src/api/evidence_test.py`, `src/api/status.py`, `src/api/privacy.py`. B: `src/api/sdg.py`, `src/api/badges.py`. | `src/app.py`, 6 new files |
| S0.8 | **Split hot shared files.** New type files `web/src/typesAgents.ts` (A) and `web/src/typesScoring.ts` (B). In `src/params.py`, add two empty headed sections: `# --- Agents and forecasting (owner A) ---` after the pipeline-freshness section, and `# --- Levels and learning gain (owner B) ---` at the end. In `web/src/i18n.tsx`, add marked blocks `// phase2 A` and `// phase2 B` far apart in the `MS` dictionary. | 4 files |
| S0.9 | All checks green; commit; the human pushes; both branches are created. | |

After Stage 0, `src/app.py`, `src/config.py`, `src/llm.py`, `src/usage.py`, `src/pack.py` and
`src/journey/store.py` are **frozen** until M1. A change to one of them is a request to the other
owner.

---

## 4. Contracts between the branches

Each contract is fixed here. The producer builds it; the consumer codes against it, using
fixtures until the merge. Fields are only added, never renamed or removed. New fields are optional
in TypeScript until M1.

### C1 Level descriptions (B produces; A's progress agent reads)
`data/packs/gbs_fa/levels.yaml`:
```yaml
checked: "YYYY-MM-DD"
scale:            # 0..5, labels shown everywhere; never hard-coded in the UI
  - {level: 0, label: none, meaning: "No exposure"}
  - {level: 1, label: novice, meaning: "Understands the basics and can follow along"}
  # ... up to 5 expert
rules: ["Done, not studied: ...", "Pick the highest true sentence", "Link a CV line where possible"]
skills:
  invoice_processing:
    basis: [{title: "...", url: "...", read: "YYYY-MM-DD"}]   # SkillsFuture / SFIA / other, cited
    anchors: {1: "I can ...", 2: "I ...", 3: "...", 4: "...", 5: "..."}
```
Python: `src/levels.py` → `load_levels() -> Levels`, `Levels.scale`, `Levels.anchor(skill, level) -> str`
and `Levels.skills: dict[str, SkillLevels]`. API: `GET /api/pack` gains `levels` (scale, rules, and
anchors per skill). The anchor wording is our own, based on the cited frameworks (SFIA text is
copyrighted and is not copied).

### C2 Role score (B produces in `/api/profiles/{id}/matches`, `/roles/{role_id}/explain`)
Each role gains:
```json
{
  "fit": 41.2,
  "fit_range": {"low": 32.0, "high": 40.5, "basis": "unevidenced claims one level lower; unstated 0..3"},
  "band": "fair",
  "band_label": "assumption",
  "components": [{"skill": "erp", "skill_name": "ERP", "weight": 2.0, "claimed": 2, "required": 3,
                  "points": 6.1, "evidenced": true, "evidence": "Applied receipts in SAP ...",
                  "source": "cv"}],
  "raise": [{"skill": "erp", "skill_name": "ERP", "from_level": 2, "to_level": 3,
             "points": 6.1, "via": "practice"}],
  "essentials_short": ["invoice_processing"]
}
```
`evidenced` = source `cv` or `agent_check` with non-empty evidence. `raise` lists the top three
single-skill changes, computed exactly with the fit formula.

### C3 Pathway steps (B produces in `/pathway`, `/tracks`)
Each step: `kind: "course" | "practice"`; `target_level`;
`time: {value, unit: "hours" | "weeks", basis: "reading_estimate" | "guided_hours" | "practice_estimate"}`;
`locked: bool`; `unlock: "previous_step" | "level_check" | null`. Plan totals: `study_hours`,
`practice_weeks`, `fit_after_study: {low, high}`, `fit_after_practice: {low, high}`, and
`free_share` (share of study hours that are free).

### C4 SDG matrix (B produces `GET /api/profiles/{id}/sdg?scenario=`)
```json
{
  "targets": [{"id": "4.4", "title": "...", "text": "..."}],
  "rows": [{"skill": "erp", "skill_name": "ERP", "steps": ["ms_..."]}],
  "cells": [{"skill": "erp", "target": "4.4", "hours": 3.5,
             "reasons": [{"text": "one line", "source": "TalentCorp 2024 p.23"}]}],
  "totals": [{"target": "4.4", "hours": 12.0}],
  "roles": [{"role_id": "...", "title": "...", "targets": [{"target": "8.5", "reason": "..."}]}],
  "source": "United Nations SDG targets ..."
}
```

### C5 Badges (B produces `GET /api/profiles/{id}/badges`)
`[{"id", "title", "earned_at", "rule", "evidence": {"kind": "course_done" | "level_up" | "essentials_met" | "plan_started", "ref": "..."}}]`.
A badge exists only when its rule fired on a stored event. No random or time-based badges.

### C6 Progress check (A produces; B's unlock rule reads the resulting claim)
- `POST /api/profiles/{id}/checks {skill}` → `{session_id, skill, target_level, question}`
- `POST /api/profiles/{id}/checks/{session_id}/answer {text}` → the next question, or `{result}`
- `result`: `{skill, proposed_level, met_anchors: [level], quotes: [text from the person's answers], model, engine, note}`
- `POST /api/profiles/{id}/checks/{session_id}/decide {accept: bool}` → on accept, the profile claim
  is set to `source: "agent_check"` with the quotes as evidence (through `journey.store.update_profile`).

The LLM never outputs a number. It returns, per anchor, `meets: yes | partly | no` plus quotes; code
verifies each quote is in the answers and maps the result to the highest anchor met.

### C7 Change test (A produces `POST /api/profiles/{id}/evidence-test`)
Body: `{scenario, overrides: [{kind: "automation_share", key: "<soc or task id>", value: 0..100}]}`.
Response: `{label: "test value, not real data", before: {roles: [{role_id, rank, fit}]},
after: {...}, weights: [{skill, before, after}], pathway: {before: [course ids], after: [...]}}`.
It reuses `score_role` and `plan_pathway` unchanged, saves nothing, and never touches stored evidence.

### C8 Forecast (A produces `GET /api/forecast`)
`[{series_id, kind: "employment_share" | "job_ads" | "skill_outlook", horizon, point, low, high,
model, backtest: {mase, baseline, baseline_mase}, label: "estimate", source, fetched_at}]`.

### C9 Status (A produces `GET /api/status`)
Freshness per source (last fetch, last change, next scheduled run), the last runs, fallback state
per engine, usage totals from `usage_event`, cost estimates (labelled), the fairness-test result
and date, and platform SDG totals (counts below 5 suppressed).

---

## 5. File ownership

**A (`p2-ai-experience`)**
- Backend: `src/evidence/**`, `src/collectors/**` (plus new collectors), `src/pipeline/**`,
  `src/occupations/**`, `src/intake/skill_search.py`, `src/runpod_jobs.py`, `runpod/**`,
  `src/agents/**` (new), `src/api/{agents,evidence_test,status,privacy,evidence,occupations,changes}.py`,
  `src/changes/**`, `scripts/load/**` (new), `requirements.txt`.
- Data: `data/sources.yaml`, generated `data/packs/gbs_fa/courses_*.yaml` and `resources_*.yaml`,
  `data/eval/occupation_titles_holdout.yaml` (new).
- Web: `App.tsx`, `Sidebar.tsx`, `index.css`, `i18n.tsx` (block `phase2 A`), `pages/{Overview,Trends,
  LiveIntelligence,Changes,Future,Occupations}.tsx`, new pages (`Privacy`, `Status`), `components/
  {Charts,LineChart,PipelineDiagram,Activity,EvidenceDrawer,Windows,OccupationEvidence}.tsx`, new
  `components/{AgentWindow,ProgressCheck,ChangeTest,TrendsChart}.tsx`, `typesAgents.ts`,
  `web/package.json`.

**B (`p2-scoring-pathway`)**
- Backend: `src/match/**`, `src/pathway/**`, `src/levels.py` (new), `src/intake/{extract,pii,files}.py`,
  `src/cv/**`, `src/goal/**`, `src/journey/progress.py`, `src/api/{journey,decision,cv,goal,sdg,badges}.py`,
  `src/params.py` matching / pathway / decision sections and the B section.
- Data: `data/packs/gbs_fa/{levels,practice,sdg,roles,skills,tasks,courses}.yaml`, `data/samples/**`,
  `data/eval/regression_profiles.yaml`.
- Web: `pages/{Onboarding,Roles,Pathway,Cv,Goal}.tsx`, `components/{CompareRoles,Decision,ExplainRole,
  PlanCompare,RouteCompare,TrackMap,SkillRadar,RoleTasks,journey}.tsx`, new
  `components/{ScoreWhy,SdgHeatmap,LevelPicker,Badges}.tsx`, `typesScoring.ts`, `i18n.tsx` (block
  `phase2 B`).

**Shared and frozen after Stage 0:** `src/app.py`, `src/config.py`, `src/db.py`, `src/llm.py`,
`src/usage.py`, `src/pack.py`, `src/journey/store.py`, `web/src/types.ts` (only the owner of an
endpoint edits that endpoint's existing interface), `web/src/api.ts`, `web/src/state.tsx`,
`components/ui.tsx`, `tests/conftest.py`.

**Rules both agents follow**
- New code goes in new files where possible.
- New tables live in the owner's new modules and are registered by importing that module from the
  owner's router module, so `src/app.py` never changes.
- A parameter that changes a calculation is added to `context_hash` in `src/changes/store.py`; that
  one-line edit is allowed for B.
- B alone bumps `CALCULATION_VERSION`.
- Tests: each branch adds new files `tests/test_<area>.py`. Tests use fakes, never paid services.
- Every new library, model, dataset or API goes in `docs/DECLARATION_LOG.md` with its licence.
  Decisions go in `docs/decision_log.md`.

---

## 6. Branch B: scoring and pathway (Meiirman)

The order is the order of work. Stage 1 (B1–B4) comes before M1.

**B1 Correctness fixes**
- Scenario factor floor: `factor = max(SCENARIO_FACTOR_FLOOR, 1 + d·s·a)`, with
  `SCENARIO_FACTOR_FLOOR = 0.1` as a declared parameter (a skill can lose most weight but never
  vanish or go negative). Invariant tests: weights > 0 for every intensity in
  `SENSITIVITY_INTENSITIES`; essentials are unchanged; results are reproducible.
- ERP miss: a deterministic backstop in `intake/extract.py`. When the CV names SAP, Oracle, Dynamics,
  NetSuite or similar, an `erp` claim is proposed with that CV sentence as evidence, even if the LLM
  missed it. The alias list is declared in `src/params.py`. Test it with a synthetic CV that says
  "SAP S/4HANA".
- Totals mismatch (6.2 h vs 8.5 h on one screen): reproduce it with the test CV that showed it, find
  the two sources of the totals, and keep one definition.
- Thin profile (everything skipped) and an unknown skill: no crash, a clear "not stated" state, and
  a fit range from 0 to the unstated-high level. Add tests.

**B2 Level scale 0–5 and descriptions (C1)**
- `levels.yaml` for every skill used by the destination roles. Draft from the team's level-description
  research (SkillsFuture Accountancy job tasks, SFIA, UF AP competency), then review. `src/levels.py` loader with tests (every skill a role
  needs has five anchors; levels are complete).
- Scale change: `PROFICIENCY_LABELS` (6 labels), `MAX_LEVEL = 5`, and the extraction prompt uses the
  anchors as its rubric. `ROLE_TIER_LEVEL` stays core 3 / upskill 2 / support 2, now meaning
  "working: full task alone" and "aware: routine tasks with guidance". Bump `CALCULATION_VERSION`.
  Log the decision.
- Onboarding skills step: `LevelPicker` shows the anchor sentences (highest true one) instead of
  numbers, with the CV line beside it when one exists.

**B3 Fit range, band, components, what would raise it (C2)**
- Range: compute fit as claimed, and again with each unevidenced claim one level lower. Combine
  with the existing unstated range in `match/decision.py`.
- Band thresholds as declared parameters (for example strong ≥ 75, good ≥ 55, fair ≥ 35, else low),
  labelled as an assumption.
- `ScoreWhy` panel: opened from a large score chip on every role. It shows the formula with the
  person's numbers, each component's points, evidence or "self-rated", the source and date, the
  label, and "what would raise it". Essentials still short are always visible.

**B4 Study versus practice (C3)**
- Parameters: `STUDY_MAX_LEVEL = 2`; `LEVEL1_MIN_HOURS = 1`; `LEVEL2_MIN_HOURS = 20` with at least
  one `hands_on` course; practice tasks for level 3 with a weeks estimate. Each one carries its basis
  (MQF 40 notional hours per credit, AAT, WSQ, PL-300 guidance) and is labelled an estimate.
- `data/packs/gbs_fa/practice.yaml`: per skill, the work tasks that move it from 2 to 3 (for example
  "reconcile a supplier statement end to end"), each with weeks and a basis. They are suggestions,
  not courses.
- Planner: study steps, then practice steps. Two fit ranges (after study, after practice). Durations
  show their `time_basis`. Practice steps unlock after the study steps on that skill; level-3 credit
  needs a re-rate or a progress check (C6).

**B5 Plan adapts to the person**
- Skip AI basics when the profile has evidenced data or AI skills at level 3 or above, or AI and
  automation work in the CV (declared rule). Say why on screen.
- Course choice follows the claimed level: no beginner course for a skill already at 2 or above.
  Advanced people get practice and project steps.

**B6 Personas and the journey test**
- Add a fourth synthetic CV, `data/samples/kavitha.txt` (senior reporting analyst, 9 years: Power
  Automate flows, Python scripts, S/4HANA migration UAT, multi-source Power BI). It is labelled
  synthetic like the others.
- `tests/test_personas.py`: Hafiz, Mei, Nur and Kavitha through the API produce different top
  roles or routes. AI basics appear for Hafiz and not for Kavitha; Kavitha's plan has practice steps
  and no beginner courses. This is the "not hard-coded" proof.

**B7 SDG mapping and heatmap (C4)**
- Extend `sdg.yaml` with per-skill and per-role links, each with a one-line reason and its source.
  Every role and skill has at least one link.
- `GET /sdg` sums planned hours per target along the person's path.
- `SdgHeatmap` on the plan page (skills × targets; a click opens the reason and source) and a compact
  version on the roles list (roles × targets), so a person can compare roles by contribution. Use the
  sequential colour rules of the dataviz skill; values are labelled "planned hours".

**B8 Progress and badges (C5)**
- Badges from stored events only: first step done, a skill level raised (re-rate or check), all
  essentials met, plan started. A `Badges` strip on the plan page.

**B9 Data for the report**
- `scripts/kpis.py` computes, from the pack and API: free-course coverage of required skills (Phase 1
  baseline 27/37, 73%; target ≥ 90%), the free share of a typical pathway, and the share of displayed
  numbers that carry a source and a date.
- Surface the paired-profile fairness test result as JSON for `/api/status`.

---

## 7. Branch A: AI and experience (Moo7x)

Stage 1 (A1–A4) comes before M1.

**A1 Navigation and Overview**
- Sidebar follows the demo's six stages: Profile → Future skills radar → Ranked roles → Pathway →
  SDG contribution → Compare futures. Evidence pages stay under "Evidence".
- Overview is the landing page: top role with band and range, what changed for you with its date,
  next step this week, scenario switch, the combined trends chart, and the SDG totals. It codes
  against C2–C5 (fields optional until M1). Visual direction comes from the reference screenshots.
- Every number has a large "Why?" control that opens `EvidenceDrawer`, which is extended into the
  shared explanation panel.

**A2 One trends chart, plus forecasts (C8)**
- `TrendsChart`: one chart with a Skills / Roles toggle. Rising goes right, declining goes left,
  each bar carries its source and date, and a click opens the detail. It replaces the scattered charts.
- Forecasting in `src/evidence/forecast.py`. Candidate models per series are seasonal-naive and
  naive baselines, damped trend and exponential smoothing (already in the repo), plus
  `statsforecast` AutoETS / AutoARIMA. A model is used only if rolling-origin backtest MASE beats
  the baseline; otherwise the baseline is shown and says so. Prediction intervals are shown.
- Series: OpenDOSM employment shares by occupation group (annual), and DOSM job-ad counts
  (quarterly; series breaks per `JOB_AD_BREAK_RATIO` are respected).
- Skill outlook: the demand forecast of the occupations that need a skill, combined with its
  observed AI-use direction, kept as separate components and labelled an estimate. Never an
  "automated" verdict.

**A3 Change test and refresh (C7)**
- `ChangeTest` panel on the radar stage: choose an occupation or task, move its AI-use share, and
  see before → after for weights, role ranks and pathway order. Labelled "test value, not real
  data"; a reset button.
- Refresh in the demo: a "Run now" button on Live intelligence that asks for the admin token, plus
  the existing replay of earlier releases.

**A4 Robustness of the evidence layer**
- Source down: each collector failure keeps the last good snapshot, which the screen labels with
  its fetch date. Add tests with a failing fake source.
- Watchdog: a run still marked "running" after a declared timeout is closed as failed.
- Web: after a redeploy, a failed lazy-loaded page reloads once instead of showing a blank page.
- Every remote call (LLM, RunPod) has a time budget and a labelled fallback, recorded in `usage_event`.

**A5 Search and RunPod**
- Hybrid retrieval in `occupations/detect.py` and `intake/skill_search.py`: BM25 and BGE-M3 dense
  results fused by reciprocal rank fusion, then reranked by bge-reranker-v2-m3. BM25-only stays as
  the labelled fallback.
- A fresh held-out evaluation set `data/eval/occupation_titles_holdout.yaml` (English and Malay),
  frozen before tuning. Report top-1 / top-3 for keyword, dense, hybrid and hybrid+rerank in
  `docs/RUNPOD_EVAL.md`.
- RunPod also embeds and reranks catalogue items (A6) and video/article passages (A7).

**A6 Course and resource catalogue as a pipeline job**
- A collector for the Microsoft Learn Catalog API (free, no key). Modules and paths with level,
  duration and URL are mapped to pack skills by BGE-M3 plus the reranker, and written as candidates
  (`verified: false`) to `data/packs/gbs_fa/courses_mslearn.yaml`, `time_basis: reading_estimate`.
- A reviewer promotes a candidate to `verified: true` only after opening it. Only verified items are
  recommended.
- Add OpenLearn and checked YouTube and articles the same way. More intermediate and advanced
  material is needed for B5.
- `scripts/check_links.py`: every course, video and article URL answers; it runs in the pipeline and
  before the pitch.

**A7 Visible resource-scout agent (attempt; fallback is the step log)**
- `src/agents/`: a coordinator with two tools-only scouts.
  - **Video scout:** captions with timestamps (`youtube-transcript-api`) → 30–90 s chunks → RunPod
    rerank against the person's gap skill and level → top segments with start and end times and a
    one-line reason → `https://youtu.be/<id>?t=<s>`.
  - **Article scout:** fetch the page (`trafilatura`) → passages → rerank → quote check (each quote
    must exist in the page text) → a deep link with a text fragment (`#:~:text=`) that opens the
    original scrolled to and highlighting the passage.
- Only registered or catalogue resources are scouted. Results are cached in the pipeline, and a live
  run has a time budget.
- `AgentWindow`: an in-app window that streams the agent's steps (server-sent events) and shows
  what it is reading. With Playwright, it shows real page screenshots with the passage highlighted;
  without it, a reader view with highlights. It closes into a results card on the plan step.
- The agent finds and points; it does not teach. Its results are labelled with `AGENT_MODEL`, the
  engine and the time.

**A8 Progress-check agent (C6)**
- `ProgressCheck` chat window, opened from a plan step. A finance-practitioner persona (system
  prompt plus retrieval of the skill's anchors, O*NET tasks and the step's practice task; not
  fine-tuned).
- It asks 2–4 concrete questions about work the person did, judges against the anchors as in C6,
  and proposes a level. The person accepts or declines. An accepted check unlocks the next steps
  (B4). Declining keeps the plan as it was. "Continue anyway" is allowed and labelled.
- Tests use a fake LLM: quotes that are not in the answers are rejected, and numbers from the model
  are never used.

**A9 Privacy, status, load test**
- Privacy: `DELETE /api/profiles/{id}` (profile, progress, checks, goal), `GET /api/profiles/{id}/export`,
  a resume code (the id as text and QR), and retention: profiles idle longer than a declared number
  of days are deleted by the pipeline. A Privacy page maps the PDPA's seven principles to what the
  app does (PII stripped before the LLM, no names stored, anonymous id, export, delete, retention).
  Onboarding's consent step is built by B with this wording.
- Status page (C9): freshness, runs, fallbacks, usage and cost, fairness result, platform SDG totals.
- Load test: `scripts/load/locustfile.py` runs the full journey (profile → matches → pathway → sdg →
  forecast) at 25, 50 and 100 users against the deployed app. LLM and RunPod calls are capped or use
  cached paths. p50 / p95, error rate and fallback behaviour go into `docs/LOAD_TEST.md`.
- Cost model `scripts/cost.py`: measured usage per journey × prices → RM per user and RM per month
  at 1k and 10k users. Measured and projected values are kept separate.

**A10 Stay and adapt (stretch)**
- On "Today → Future you": the person's current tasks, the AI-use evidence for each (observed,
  kept separate from exposure), the responsibilities that grow, and the skills shared with the
  destination roles. No time-saved percentages unless declared and labelled (the team's AI
  time-savings research is the basis if added).

---

## 8. Integration on `main` after M2

1. Mount A's `AgentWindow` and `ProgressCheck` on B's plan steps (`TrackMap`), using the props
   fixed in C6/C7.
2. Overview reads the real C2–C5 fields; drop the fixtures.
3. Put the `SdgHeatmap` summary on Overview.
4. Full persona journey test, load test, link check, `scripts/kpis.py`; record the results.
5. Update `docs/explain/*`, `README.md`, the declaration log and the decision log.

---

## 9. Evidence for the final report (Section 4) and the judges

| Requirement | Where it comes from | Owner |
|---|---|---|
| Reach: who first, which channel, how many | Report text: TVET and university career centres, then employers' L&D; realistic numbers with the reasoning | Moo7x |
| Data freshness | `/api/status` freshness, run history, scheduled job | A |
| Cost per user / month | `usage_event` + `scripts/cost.py`, load test | A |
| Learning cost | `free_share` (C3), `scripts/kpis.py`; HRD Corp: none verified yet, said openly | B |
| Measured SDG impact vs Phase 1 targets | `scripts/kpis.py` (coverage, traceability), a timed test with 10+ people using synthetic personas (time to a plan < 5 min; ≥ 70% can explain their top role), platform SDG totals | both |
| Privacy (PDPA) | Privacy page, delete/export/retention, PII stripping | A |
| Fairness | Paired-profile test result surfaced on status | B |
| 4.1 proof | Fit formula, scenario factor, learning-gain rule, forecast backtest table, load-test log | both |

**Demo questions and what answers each one**

| Question | Answer on screen | Who answers |
|---|---|---|
| Change the trend data now. What should change? | Change test (A3) and the replay | Moo7x |
| Where does this come from? Is this course or number real? | "Why?" panel, source and date, link check, catalogue `verified` | Meiirman |
| Why this score, and what would raise it? | `ScoreWhy` (B3) | Meiirman |
| How is the data kept current, and what does it cost? | Status page (A9) | Moo7x |
| What if AI moves faster or slower? | Compare futures and the sensitivity view | Meiirman |
| How do you stop invented jobs or courses? | Pack plus verified catalogue, quote checks, `verified: false` never recommended | Moo7x |

---

## 10. Definition of done (every work package)

- It works through the real API on the deployed app, not only with mocks; frontend types match the
  server shapes.
- Every number shown is labelled observed, assumption or estimate, with its source and date; a
  missing value shows "not stated", never 0.
- New parameters are named and commented (what, why, which kind) and logged in
  `docs/decision_log.md`.
- Tests cover the rule, including the edge cases (thin profile, missing data, failing source,
  fallback).
- Checks are green; the commits are small; `docs/explain/<module>.md` is updated.
