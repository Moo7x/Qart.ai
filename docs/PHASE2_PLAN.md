# Qart.ai Phase 2 (finalist) plan

The work plan for the finalist round: what is built, by whom, in which files, to which rules, and
how the two branches merge without conflicts. It extends `docs/PLAN.md` (the product and system
design); where the two differ, this file wins.

**How a coding agent uses this file**
1. Read `AGENTS.md`, then §0–§6 of this file, then your own branch's section (§7 for owner A, §8
   for owner B). Read the other branch's section only for context.
2. Work through your section's work packages in order. Each package lists its goal, the files you
   may touch, the exact rules, the tests that prove it and what is out of scope.
3. Touch only the files your branch owns (§5). Anything else is a request to the other owner,
   written in the commit body and raised by the human. Never edit it yourself.
4. When this plan is silent or two rules conflict, stop and ask the human. Do not guess, and do not
   add, remove or reinterpret a feature. Record each answer in `docs/decision_log.md`.
5. Stage 0 (§3) is **done**. Do not redo, move or "improve" it.

| Branch | Owner | Theme |
|---|---|---|
| `p2-ai-experience` | Moo7x (A) | Navigation and Overview, trends and forecasting, pay data, change test and refresh, evidence robustness, search and RunPod, course catalogue pipeline, visible scout agent, progress-check agent, privacy, status, load test, cost |
| `p2-scoring-pathway` | Meiirman (B) | Correctness fixes, 0–5 described levels, fit range and band, "what would raise it", pay on role cards, study versus practice, adaptive plan, personas, SDG mapping and heatmap, progress events and badges, report figures, more GBS finance roles |

The UI redesign is a separate last phase (§10), after both branches are merged.

---

## 0. What the finalist round requires

From the Domain 1 Finalist Guide and the finalist report template. Every work package below traces
to one of these.

- **One live journey, six stages, one synthetic user:**
  1. profile intake (skills drive the results, nothing pre-filled);
  2. Future Skills Radar (rising and declining skills **and roles**, with source and date);
  3. ranked roles with reasons, plus "why this score, and what would raise it";
  4. pathway with real, checkable courses;
  5. SDG contribution;
  6. compare futures (switch scenarios and show the shift).

  A must-have that is missing, or only described, caps Problem–Solution Fit.
- **Live checks by judges:**
  - "Change the trend data now. What should change?"
  - "Is this course, job or number real?"
  - "Why this score, and what would raise it?"
  - "How is the data kept current, and what does it cost?"
  - "What if AI moves faster or slower?"
  - "How do you stop the system inventing a job or a course?"
- **Technical expectations:**
  - a trend pipeline with the fetch date stored and shown, and a refresh possible during the demo;
  - a decomposable score with "what would raise it";
  - recommendations built from our own sourced tables, with the source cited on each, saying so
    when no source exists, and naming the model;
  - scenarios driven by explicit parameters;
  - an SDG map with a one-line reason per link, added up into the person's path;
  - robustness to a thin profile, an unknown skill and an unavailable source (last good snapshot).
- **Final report Section 4 (every claim backed by numbers):**
  - reach and channel;
  - data freshness;
  - cost per user or per month;
  - learning cost (share free or low cost);
  - measured SDG impact against our Phase 1 targets, with how it was verified;
  - PDPA privacy;
  - fairness checks;
  - optional 4.1 proof (code, formula or logs that reflect what was built).
- **Our Phase 1 commitments:**
  - verified free-course coverage from 27/37 required skills (73%) to at least 34/37 (90%+);
  - at least 80% of 10+ test users reach roles and a pathway in under 5 minutes;
  - at least 70% can explain why their top role was recommended;
  - 100% of displayed numbers keep their source and date.
- **Process:**
  - steady small commits through the 48-hour sprint (the report's §3.2 asks what was built in it);
  - a backup (offline build or recording), prepared later, after the UI phase (§1 decision 15);
  - more than one teammate able to answer each Q&A question.

---

## 1. Decisions for Phase 2

Decided by the team. Each is logged in `docs/decision_log.md` (2026-10-30).

1. **Users:** working adults, juniors / fresh graduates and students. **No HR / L&D view**, and no
   company-level aggregates.
2. **Levels 0–5, each described by an "I can…" sentence per skill.** Labels: 0 none · 1 novice ·
   2 aware · 3 working · 4 proficient · 5 expert, aligned with SFIA's lower five levels.
   - **Rules:** done, not studied (level 3 and above need work experience; study alone reaches level 2
     at most); pick the highest true sentence; link a CV line where possible.
   - **Stored levels keep their numbers.** The old guide (1 mentioned or studied · 2 did it in a job ·
     3 did it routinely or was responsible · 4 led, taught or improved it for others) matches the new
     descriptions 1–4 one to one. Level 5 is new.
   - **Role requirements keep their numbers:** core 3 ("working: handles the full task alone"),
     upskill and support 2 ("aware: routine tasks with guidance").
3. **A progress-check agent may assess.** A finance-practitioner agent asks about work the person
   did, judges it against the level descriptions and proposes a level. The person accepts or
   declines. Accepted results are claims with source `agent_check`, never "verified". The app never
   tutors or hints at answers and never makes hiring, promotion or dismissal decisions.
4. **Study and practice are separate.** Study moves a skill to level 2 at most; level 3 needs a
   practice task at work, checked by a re-rate or the progress check. Plans show two fit ranges:
   after study and after study and practice. Course durations show what they measure.
5. **Fit is shown as a band with a range**, its components and what would raise it, in a large,
   clickable panel, never small print.
6. **The plan adapts to the person.** AI basics are skipped when the CV shows AI or automation
   work; no beginner course for a skill already at level 2 or above; advanced people get practice
   and project steps.
7. **SDG contribution is a heatmap** (skills × SDG targets, cells = planned study hours, a click
   opens the one-line reason and source) with a total per target and a roles × targets view for
   comparing roles.
8. **Forecasting is part of the product.** The brief asks to *predict* emerging and declining skills
   and jobs. Each series gets forecasts from several models, chosen by rolling-origin backtest
   against a naive baseline; the baseline is kept and shown when it wins. Labelled estimates.
9. **The visible resource-scout agent is attempted.** It finds the exact part of a video or article
   that serves a gap, in an in-app agent window. Level 1 (must): a step log and a reader view with
   highlights. Level 2 (stretch): real page screenshots.
10. **Models:** `gpt-4o-mini` (`LLM_MODEL`) for CV extraction and explanations; `gpt-4.1-mini`
    (`AGENT_MODEL`) for agents. Both are named on screen and in the declaration.
11. **No login.** The anonymous 128-bit profile id stays; add a resume code, export, delete and a
    90-day retention limit.
12. **Pay on every role card.** The OpenDOSM median and mean monthly wage of the role's MASCO major
    group, observed, with year and source. It is labelled "pay of all employees in this
    occupation group, not an offer for this role". Pay never changes fit or rank.
13. **More GBS finance roles.** The pack grows beyond 9 destination roles with every finance-function
    role the TalentCorp (2024) study names with a skill list (B10). Nothing is added without a
    cited page.
14. **The UI redesign is the last phase (§10).** Until then, both branches keep the current look
    and sections and change structure only where a package requires it. After M2 the owner walks
    through the app; the agreed changes are written into §10 and applied page by page by the page
    owner.
15. **Later, not in this phase:**
    - funding and training requests (HRD Corp, PERKESO, MyMahir);
    - weights from job-post skill frequencies;
    - Chinese interface;
    - route options (shortest / flexible / targeted);
    - an auto-generated video;
    - a second field pack;
    - the final report, deck, declaration update, backup recording and offline build (after the UI
      phase).
16. **Not built at all:**
    - an agent team (several AI agents working together); the scout is one agent with code tools;
    - simulated AI users walking the app; concurrency is proven by the load test only (A9);
    - a personal evidence graph; the existing Live intelligence diagram stays as it is;
    - "stay and adapt" (current-role task changes) and AI time-saving estimates.

---

## 2. Branches and merging

**Starting**
- Both branches start from `main` at or after commit `e123c72` (Stage 0).
- If a branch was created before this plan was last updated, run `git merge main` on it to take
  the update.

**While working**
- Commit small steps (`area: what changed`), no AI attribution lines.
- Before each commit run all checks:
  `ruff format . && ruff check . && mypy src && pytest -q`; in `web/`: `npm run lint && npm run build`.
- Never merge one branch into the other. Never rebase, squash, force-push or `reset --hard`.
- Agents never push; the human runs `git push origin <branch>`.

**Merge points**
- **M1, early merge:** after B1–B4 and A1–A4 are done. It catches incompatibilities while they are
  small.
- **M2, final merge:** when both branches are done. Integration (§9) follows on `main`, then the
  UI phase (§10).

At each merge point, in this order:
1. **B into main:**
   ```
   git switch main
   git pull origin main
   git merge --no-ff p2-scoring-pathway
   ```
   Run all checks, then `git push origin main`.
2. **A takes main in:** `git switch p2-ai-experience`, then `git merge main`. Fix, then run all checks.
3. **A into main:**
   ```
   git switch main
   git merge --no-ff p2-ai-experience
   ```
   Run all checks, then `git push origin main`.
4. **B takes main in:** `git switch p2-scoring-pathway`, then `git merge main`.

B goes first because B changes data A only reads (the level scale and score fields).

**Merge checks:** all checks above, plus a manual run of the six-stage journey with the four
personas on a local build.

**Conflicts**
- In `docs/decision_log.md`, `docs/DECLARATION_LOG.md` and `docs/explain/*`: keep both entries.
- In code: the owner of that file (§5) resolves it.

**Deploying:** Replit deploys `main` only, at the human's request. Do not republish while a judge
may be using the app.

---

## 3. Stage 0: shared contracts (DONE on `main`)

Committed before branching, so neither branch has to edit these shared files.

| Commit | What it gave both branches |
|---|---|
| `bea812d` | This plan; `AGENTS.md` and the `docs/PLAN.md` header point to it |
| `573cd2a` | `src/llm.py`: `openai_complete(settings, *, schema_name, purpose, timeout, temperature=0, model=None)`, the one JSON-schema LLM call; the three existing call sites use it. `src/usage.py`: the `usage_event` table and `record(...)`; every OpenAI and RunPod call stores purpose, engine, model, tokens, seconds and success (no content); `totals(engine)` sums them; bound at app and pipeline start-up |
| `96d5432` | `Settings.agent_model` (`AGENT_MODEL`, default `gpt-4.1-mini`); `SkillClaim.source` accepts `"agent_check"`, with `checked_at` (ISO text) and `model` |
| `428d474` | `Course` fields `time_basis` (`reading_estimate` / `guided_hours` / `stated`), `hands_on`, `checked`, `verified` (`False` = candidate, never planned); every `courses_*.yaml` and `resources_*.yaml` loads beside the hand-checked files (`pack_files(stem)`) |
| `acc813f` | Empty routers registered in `src/app.py`. A: `src/api/agents.py` (`/api`), `src/api/evidence_test.py` (`/api/profiles/{profile_id}`), `src/api/status.py` (`/api`), `src/api/privacy.py` (`/api/profiles/{profile_id}`). B: `src/api/sdg.py`, `src/api/badges.py` (both `/api/profiles/{profile_id}`) |
| `bd7c8b2` | `web/src/typesAgents.ts` (A) and `web/src/typesScoring.ts` (B); headed sections in `src/params.py` (A after pipeline freshness, B at the end); marked blocks `// phase2 A` and `// phase2 B` in `web/src/i18n.tsx` |
| `e123c72` | Declaration-log entries for `AGENT_MODEL` and the Stage 0 tooling |

**Rules that follow from Stage 0**
- Every new LLM call goes through `src/llm.py`, or, for tool-calling agents, through A's agent
  client, which records usage with `src/usage.record`.
- A new route goes into one of the owner's registered router modules. **No new router module**:
  it would need an `src/app.py` edit.
- A's extra profile routes go in `evidence_test.py` or `privacy.py`, global ones in `status.py`
  or `evidence.py`, and agent routes in `agents.py`.

---

## 4. Contracts between the branches

The producer builds the contract; the consumer codes against it, using fixtures until the merge
that delivers it.

**Rules**
- Fields are only added, never renamed or removed. New TypeScript fields stay optional (`?`) until
  the merge that delivers them: C2, C3 and C11 at M1; C4, C5, C6, C9 and C10 at M2.
- New endpoints return Pydantic models declared in the router module, mirrored exactly in the
  owner's types file.
- Every number carries its kind: observed (source and date), assumption or estimate.

### C1 Level descriptions (B produces; A's progress agent reads)
File `data/packs/gbs_fa/levels.yaml`:
```yaml
checked: "YYYY-MM-DD"
scale:
  - {level: 0, label: none, meaning: "No exposure"}
  - {level: 1, label: novice, meaning: "Understands the basics and can follow along"}
  - {level: 2, label: aware, meaning: "Does routine tasks with guidance or a template"}
  - {level: 3, label: working, meaning: "Handles the full task alone, including common problems"}
  - {level: 4, label: proficient, meaning: "Handles complex cases, improves the process, guides others"}
  - {level: 5, label: expert, meaning: "Sets standards or direction for a team, function or region"}
rules:
  - "Done, not studied: levels 3 and above need work experience; study alone counts as level 2 at most."
  - "Pick the highest sentence that is true for your work in the last two years."
  - "Link a CV line where possible."
skills:
  invoice_processing:
    basis:
      - {title: "SkillsFuture Skills Framework for Accountancy (May 2026)", url: "https://...", read: "YYYY-MM-DD"}
    anchors:
      1: "I can explain the steps from purchase order to payment, including a three-way match."
      2: "I enter and code invoices under review, and check goods were received before posting."
      3: "I handle my own invoice queue end to end, including credit notes and exceptions."
      4: "I resolve complex AP errors, reconcile AP to the ledger, and train other processors."
      5: "I design the AP process and controls for an entity or service centre."
```
- **Python:** `src/levels.py` provides `load_levels() -> Levels`; `Levels.scale`; `Levels.rules`;
  `Levels.anchor(skill_id, level) -> str`; `Levels.skills: dict[str, SkillLevels]`.
- **API:** `GET /api/pack` gains `"levels": {"scale": [...], "rules": [...], "skills": {skill_id: {"anchors": {...}, "basis": [...]}}}`.
  The existing `"proficiency"` list becomes the six labels.
- **Wording:** anchors are our own sentences, based on the cited frameworks. SFIA text is copyrighted
  and is never copied.
- **UI:** level labels are never hard-coded; they always come from `/api/pack`.

### C2 Role score (B adds to every role in `GET /api/profiles/{id}/matches`)
Existing fields stay (`fit`, `requirements`, `meters`, `fit_range`, …). `fit_range` gets the new
definition below. Added:
```json
{
  "fit_range": {"low": 32.0, "high": 47.5,
                "basis": "low: self-rated claims one level lower, unstated as none; high: unstated at working"},
  "band": "fair",
  "band_basis": "assumption",
  "components": [{"skill": "erp", "skill_name": "Enterprise Resource Planning (ERP)", "weight": 1.0,
                  "claimed": 2, "required": 2, "points": 6.1, "evidenced": true,
                  "evidence": "Applied incoming customer receipts ... in SAP", "source": "cv"}],
  "raise": [{"skill": "dashboards", "skill_name": "...", "from_level": 1, "to_level": 2,
             "points": 7.4, "via": "study"}],
  "essentials_short": ["financial_reporting"]
}
```
- `fit` stays exactly as computed today: as stated, with unstated counted as 0.
- `fit_range.low` lowers each **unevidenced** claim (source `self` or `keyword`) by one level
  (minimum 0), with unstated as 0. `fit_range.high` uses claims as stated, with unstated at
  `UNSTATED_HIGH_LEVEL`.
- `band` comes from `fit`: strong ≥ 75 · good ≥ 55 · fair ≥ 35 · low below. These are declared
  parameters, labelled "assumption".
- `evidenced` = source `cv` or `agent_check`, with non-empty evidence.
- `raise` = the three single-skill changes with the most fit points, each computed exactly by
  re-scoring. `via`: `study` if the target level is ≤ `STUDY_MAX_LEVEL`, `practice` if above, and
  `check` if the skill is already at its level but unevidenced.

### C3 Pathway (B adds to `/pathway` and to the nodes of `/tracks`)
Each step:
```json
{"order": 1, "kind": "course" | "practice", "id": "ms_core_data_concepts", "skill": "data_management",
 "target_level": 2,
 "time": {"value": 0.6, "unit": "hours" | "weeks", "basis": "reading_estimate" | "guided_hours" | "practice_estimate",
          "low": null, "high": null},
 "locked": false, "unlock": "previous_step" | "study_done" | "level_check" | null}
```
Plan totals:
- `study_hours`;
- `practice_weeks: {low, high}`;
- `fit_after_study: {low, high}` and `fit_after_practice: {low, high}`;
- `free_share` (share of study hours in free courses, 0–1);
- `ai_basics: {"shown": bool, "reason": "..."}`.

The existing `total_hours` stays and equals `study_hours`.

### C4 SDG matrix (B produces `GET /api/profiles/{id}/sdg?scenario=`)
```json
{
  "targets": [{"id": "4.4", "title": "...", "text": "official UN wording"}],
  "rows": [{"skill": "erp", "skill_name": "...", "steps": ["ms_..."], "practice": true}],
  "cells": [{"skill": "erp", "target": "4.4", "hours": 3.5,
             "reasons": [{"text": "one line", "source": "TalentCorp (2024) p. 23"}]}],
  "path_links": [{"target": "4.3", "text": "...", "source": "..."}],
  "totals": [{"target": "4.4", "hours": 12.0}],
  "roles": [{"role_id": "...", "title": "...", "targets": [{"target": "8.5", "reason": "..."}]}],
  "note": "Hours count toward every target a skill serves, so totals are not added across targets.",
  "source": "United Nations SDG targets, sdgs.un.org/goals (read ...)"
}
```
Pure function, also used by A's status page: `src/pathway/sdg.py: sdg_matrix(pack, pathway) -> SdgMatrix`.

### C5 Progress events and badges (B produces)
- **Events:** table `journey_event` (`profile_id`, `at`, `kind`, `ref`, `before`, `after`). Kinds:
  `course_done`, `course_undone`, `step_skipped`, `level_changed` (with source), `destination_chosen`.
  Written by B's routes.
- **Exception:** A's progress-check decide route writes `level_changed` through B's function
  `src/journey/events.py: record_event(engine, profile_id, kind, ref, before, after)`.
- **Badges:** `GET /api/profiles/{id}/badges` →
  `[{"id", "title", "earned_at", "rule", "evidence": {"kind", "ref"}}]`, derived only from events.
- **`PUT /progress`** gains `skipped: list[str]` (steps passed with "continue anyway", labelled).

### C6 Progress check (A produces; B's unlock rule reads the resulting claim)
- `POST /api/profiles/{id}/checks {skill}` → `{session_id, skill, current_level, target_level, question, model}`
- `POST /api/profiles/{id}/checks/{session_id}/answer {text}` → `{question}` (next) or `{result}`
- `result`: `{skill, proposed_level, met: [{level, verdict: "yes"|"partly"|"no", quote}], model, engine, note}`
- `POST /api/profiles/{id}/checks/{session_id}/decide {accept: bool}`. On accept, the claim becomes
  `{level: proposed_level, source: "agent_check", evidence: <joined quotes>, checked_at, model}`
  through `journey.store.update_profile`, plus a `level_changed` event (C5).

### C7 Change test (A produces `POST /api/profiles/{id}/evidence-test`)
- **Body:** `{scenario, overrides: [{kind: "occupation_share" | "task_share", key: "<SOC code or O*NET task id>", value: 0..100}]}`
- **Response:**
  `{label: "Test value, not real data", overrides, before: {roles: [{role_id, title, rank, fit}]}, after: {...}, weights: [{role_id, skill, before, after}], pathway: {role_id, before: [course ids], after: [...]}}`
- It uses `dataclasses.replace` on `Evidence` and the unchanged `rank_roles`, `score_role` and
  `plan_pathway`. Nothing is saved; stored evidence is never touched.

### C8 Forecast (A produces `GET /api/forecast`)
```json
[{"series_id": "employment_share:professionals", "kind": "employment_share" | "job_ads" | "skill_outlook" | "role_outlook",
  "title": "...", "history": [{"period": "2025", "value": 13.9}],
  "forecast": [{"period": "2027", "point": 14.3, "low": 13.6, "high": 15.0}],
  "model": "damped_trend", "baseline": "naive",
  "backtest": {"mase": 0.82, "baseline_mase": 1.0, "origins": 9},
  "label": "estimate", "source": "OpenDOSM wages_occupation", "fetched_at": "..."}]
```

### C9 Status (A produces `GET /api/status`)
- **Freshness per source:** `last_attempt_at`, `last_success_at`, `last_change_at` and
  `serving_snapshot_from`.
- **Runs:** the last 12, plus the next scheduled run.
- **Fallback state** per engine.
- **Usage totals** from `usage_event`, and labelled cost estimates.
- **Fairness result** with its date (C10).
- **Platform SDG totals** from C4 over all profiles with a destination, suppressed below 5 profiles.

### C10 Fairness check (B produces; A displays)
`src/match/fairness.py: paired_profile_check(pack, evidence) -> {"pairs", "identical", "max_fit_difference", "checked_at"}`.
It is pure: the same synthetic pairs as `tests/test_fairness.py`, which differ only in protected
attributes.

### C11 Pay by occupation group (A collects; B shows on role cards)
- **A stores**, in the `dosm_wages_occupation` collector (both sexes, per major group and year,
  next to the existing `employees` series):
  - series `wages_median`, unit `RM per month`;
  - series `wages_mean`, unit `RM per month`.

  Same `entity` names as today (`professionals`, `technicians`, `clerical`, `overall`), and the
  cited span is the published row. The collector's `METHOD_VERSION` stays `dosm_wages/1`: the pay
  comes from the same rows, read the same way, and a new version would store every headcount row
  again. Code that computes employment shares reads only the `employees` series
  (`measures.is_headcount`).
- **B adds to each role card** in `/matches`:
  ```json
  {"pay": {"group": "professionals", "group_title": "Professionals", "year": "2025",
           "median": 5200, "mean": 6100, "overall_median": 2900, "unit": "RM per month",
           "kind": "observed", "source": "OpenDOSM wages_occupation", "fetched_at": "...",
           "note": "Pay of all employees in this occupation group, not an offer for this role."}}
  ```
  The group comes from the role's ISCO code through `src/match/outlook.py MAJOR_GROUP`.
  `"pay": null` when the group or the year is missing (shown as "not published", never 0).

---

## 5. File ownership

**Owner A (`p2-ai-experience`)**
- **Backend:**
  - `src/evidence/**`, `src/collectors/**` (and new collectors), `src/pipeline/**`,
    `src/occupations/**`, `src/changes/**`;
  - `src/intake/skill_search.py`, `src/runpod_jobs.py`, `runpod/**`;
  - new `src/agents/**`, new `src/privacy.py`;
  - routers `src/api/{agents,evidence_test,status,privacy,evidence,occupations,changes,feedback}.py`;
  - `src/feedback/**`, new `scripts/{load,cost,check_links,review_catalogue}*`, `requirements.txt`;
  - the A section of `src/params.py` and the existing evidence and pipeline sections above it.
- **Data:** `data/sources.yaml`, generated `data/packs/gbs_fa/courses_*.yaml` and
  `resources_*.yaml`, new `data/eval/occupation_titles_holdout.yaml`, new `data/agents/**`
  (character files).
- **Web:**
  - `App.tsx`, `main.tsx`, `index.css`, `i18n.tsx` (`phase2 A` block and the navigation strings),
    `web/package.json`;
  - pages `Overview`, `Trends`, `LiveIntelligence`, `Changes`, `Future`, `Occupations`, and new
    `Status` and `Privacy`;
  - components `Sidebar`, `Charts`, `LineChart`, `PipelineDiagram`, `Activity`, `EvidenceDrawer`,
    `OccupationEvidence`, `Feedback`, and new `AgentWindow`, `ProgressCheck`, `ChangeTest`,
    `TrendsChart`, `ResumeCode`;
  - `typesAgents.ts`.

**Owner B (`p2-scoring-pathway`)**
- **Backend:**
  - `src/match/**`, `src/pathway/**`, new `src/levels.py`, new `src/journey/events.py`,
    `src/journey/progress.py`, `src/journey/store.py`;
  - `src/intake/{extract,pii,files}.py`, `src/cv/**`, `src/goal/**`;
  - `src/pack.py`, `src/resources.py`;
  - routers `src/api/{journey,decision,cv,goal,sdg,badges}.py`;
  - the B section and the matching, decision and pathway sections of `src/params.py`;
  - `CALCULATION_VERSION`, and the policy list in `src/changes/store.py` `context_hash` (that one
    list only);
  - new `scripts/kpis.py`.
- **Data:** `data/packs/gbs_fa/{levels,practice,sdg,roles,skills,tasks,courses,resources,field}.yaml`,
  `data/samples/**`, `data/eval/regression_profiles.yaml`. `field.yaml` lists the occupations the
  collectors follow, so B tells A when B10 adds one: the next pipeline run collects its evidence
  with no code change.
- **Web:**
  - pages `Onboarding`, `Roles`, `Pathway`, `Cv`, `Goal`;
  - components `CompareRoles`, `Decision`, `ExplainRole`, `PlanCompare`, `RouteCompare`, `TrackMap`,
    `SkillRadar`, `RoleTasks`, `journey`, and new `ScoreWhy`, `SdgHeatmap`, `LevelPicker`, `Badges`;
  - `typesScoring.ts`, `i18n.tsx` (`phase2 B` block and the onboarding strings).

**Frozen for both** (a change needs both owners and the human):
- `src/app.py`, `src/config.py`, `src/db.py`, `src/llm.py`, `src/usage.py`;
- `web/src/api.ts`, `web/src/state.tsx`, `web/src/components/ui.tsx`, `web/src/components/Windows.tsx`;
- `tests/conftest.py`, `.env.example`.

**`web/src/types.ts`:** the owner of an endpoint edits only that endpoint's existing types.
- B: `PackInfo`, `ProfileData`, `SkillClaim`, `MatchesResponse` and its role type, `PathwayResponse`,
  `TracksResponse` and its node types, `ProgressResponse`, `FutureResponse`, `GoalResponse`,
  `CvResponse`, `SensitivityResponse`.
- A: everything for evidence, signals, trends, runs, sources, changes, occupations, feedback.

**Shared rules**
- Every new table holding a person's data names its key column `profile_id`. A's privacy
  delete finds such tables automatically.
- New tables are registered by importing their module from the owner's router module.
- Tests: new files only, named `tests/test_<area>.py`. Use fakes for the LLM, RunPod and network.
  Never call paid services.
- Every new library, model, dataset or API goes in `docs/DECLARATION_LOG.md` with its licence, in
  the same commit.
- **The "Why?" control and panel look the same everywhere:**
  - the control: a `btn` button with the lucide `Info` icon and the word "Why?", at least 44 px
    high, next to the number it explains;
  - the panel: the existing `Windows` component with one or more panes, each showing the number,
    its kind (observed, assumption or estimate), the formula with the person's numbers, the
    source and date, and the model when one was used.

---

## 6. The demo journey these packages build

Navigation follows the six stages. Overview is the landing page.

| Stage | Page (route) | Built by | What the judge sees |
|---|---|---|---|
| Overview | `/overview` | A | Top role with band and range, what changed for you, next step this week, scenario switch, trends snapshot, SDG totals, freshness line |
| 1 Profile | `/start` (onboarding), `/cv` | B | Situation, CV with quoted evidence, level sentences, consent |
| 2 Future skills radar | `/trends` | A | One chart (Skills / Roles) with forecasts, the change test, the refresh |
| 3 Ranked roles | `/roles` | B | Band, range, `ScoreWhy`, what would raise it, roles × SDG view |
| 4 Pathway | `/pathway` | B (A's agents mounted after M2) | Study and practice steps, two fit ranges, badges, scout and progress check |
| 5 SDG contribution | `/pathway#sdg` | B | Heatmap with reasons, totals per target |
| 6 Compare futures | `/future` | A | Moderate and fast side by side, rank shifts, weight changes, sensitivity |
| Evidence | `/live`, `/occupations`, `/changes`, `/status`, `/privacy` | A | Runs, sources, replay, status, privacy |

**Personas** (synthetic, B6):
- Hafiz (graduate, beginner);
- Mei (retail supervisor switching in);
- Nur (cash application analyst at risk);
- Kavitha (senior reporting analyst, advanced).

Each must produce a visibly different result.

---

## 7. Branch A: AI and experience (Moo7x)

Stage 1 (before M1) = A1–A4.

### A1 Navigation, Overview and the "Why?" panels
**Goal:** the six-stage journey is obvious, and Overview is the landing page.

**Files:** `App.tsx`, `Sidebar.tsx`, `Overview.tsx`, `index.css`, `i18n.tsx` (A), `EvidenceDrawer.tsx`.

**Rules**
- Sidebar groups:
  - **"Your journey":** Overview, 1 Profile, 2 Future skills radar, 3 Ranked roles, 4 Pathway,
    5 SDG contribution (`/pathway#sdg`), 6 Compare futures;
  - **"Evidence":** Live intelligence, Any occupation, What changed, and Status (the link is added
    in A9 together with the page, never before it exists);
  - My goal and My CV stay reachable from Profile.
- **Overview cards, top to bottom:**
  1. top role: title, band, range and essentials short (C2), with a "Why?" that opens the
     components;
  2. what changed for you (latest proposal from `/changes`, with its date);
  3. next step this week (`/progress` `this_week`), with "Check my progress" opening A8;
  4. scenario switch;
  5. trends snapshot: the top three rising and declining skills and roles from A2, each with source
     and date;
  6. SDG totals (C4 `totals`);
  7. freshness line: the last pipeline run, and the newest fetch date per source kind.
- Fields from B stay optional until the merge that delivers them (§4 rules). With a field missing,
  the card shows its existing content or hides that line, never a placeholder number. Card 3's
  "Check my progress" appears once A8 exists.
- Every number on Overview has a "Why?" (§5 shared rules).
- **Look:** keep the current colours, type, spacing and section designs; the redesign is the last
  phase (§10). New cards and components reuse the existing classes (`card`, `btn`, `tag`, `h1`,
  `h2`, `cap`, `eyebrow`) and need no new design tokens. Mobile: no horizontal overflow at
  375 px.

**Tests:** `tsc`, lint, build. A manual check on `/overview` with each persona, and on a phone width.

**Out of scope:** B's pages.

### A2 One trends chart, plus forecasts
**Goal:** stage 2 shows rising and declining skills **and roles**, with source, date and a
forecast.

**Files:**
- `src/evidence/forecast.py` (new), `src/evidence/trends.py`, `src/api/evidence.py`;
- `src/collectors/dosm_wages.py` (pay series, C11);
- `TrendsChart.tsx` (new), `Trends.tsx`, `typesAgents.ts`, `requirements.txt`.

**Pay series first (C11):** store `wages_median` and `wages_mean` per group and year, before M1,
so B can show pay on role cards. Test the parser with the existing fixture, which already has both
fields.

**Forecast series**
- OpenDOSM employment share per MASCO major group (annual; already collected).
- DOSM online job ads (quarterly): the total and the Professionals share. Quarters flagged by
  `JOB_AD_BREAK_RATIO` are series breaks; models fit only the segment after the last break.

**Models** (each one declared and logged)
- Baselines: naive (last value) and drift (linear).
- Existing: damped trend and simple exponential smoothing.
- New: Theta (`statsmodels`, BSD-3), and a global gradient-boosting model
  (`scikit-learn` `HistGradientBoostingRegressor`, BSD-3) on lags 1–3 plus a group indicator,
  trained across all groups of one series kind.

**Model choice**
- Run a rolling-origin backtest for each series (`ROLLING_FIRST_ORIGIN`, horizons 1 and 2) and
  compute each model's MASE against naive.
- Use the lowest-MASE model only if it beats naive (MASE < 1). Otherwise show naive and say
  "no model beat keeping the last value".
- Intervals: the 10th–90th percentiles of the chosen model's backtest errors at that horizon,
  added to the point. They are empirical, not a model assumption.
- New parameters (A section of `params.py`): `FORECAST_HORIZONS = (1, 2)`, `INTERVAL_QUANTILES = (0.1, 0.9)`,
  `GBR_LAGS = 3`, `GBR_MIN_TRAIN_POINTS = 8`.

**Outlooks**
- `role_outlook` (per destination role): the forecast for its occupation's major group (via
  `src/match/outlook.py MAJOR_GROUP`), plus TalentCorp's emerging-role and impact view (expert,
  with page). They are shown as separate components.
- `skill_outlook` (per skill), with two separate components:
  - the demand forecast averaged over the destination roles that need the skill;
  - the observed AI-use direction on its linked tasks (Economic Index).

  Never combined into one "automated" verdict.

**`TrendsChart`**
- One diverging horizontal bar chart with a **Skills / Roles** toggle.
- **Skills mode:** the % weight change under the selected scenario (an assumption applied to
  observed AI use), with the skill outlook in the tooltip.
- **Roles mode:** the forecast change, in percentage points, of the role's group share over 2 years
  (estimate), with an interval whisker.
- Rising to the right, declining to the left. Each bar shows its kind tag and has a tooltip
  (value, source, date). A click opens `Windows` with the history, forecast, model, backtest and
  sources.
- Follow the dataviz rules: one axis, no dual axis, a validated palette, a table view.

**Tests:** `tests/test_forecast.py`:
- the backtest picks naive when no model beats it;
- intervals contain the point;
- forecasts never start inside a series break;
- the API shape matches C8.

**Out of scope:** forecasting the fit score itself.

### A3 Change test and refresh
**Goal:** a judge can change trend data live and see what changes, and a real refresh can run
during the demo.

**Files:** `src/api/evidence_test.py`, `ChangeTest.tsx` (new), `Trends.tsx`, `LiveIntelligence.tsx`,
`typesAgents.ts`.

**Rules**
- **Change test:** implement C7. The `ChangeTest` panel sits on the radar stage:
  1. Pick one of the person's top role's skills. It shows the linked tasks and occupation share,
     with source and period.
  2. Move a slider (0–100) and press "Apply test value".
  3. See before → after: weights, role ranks (arrows), and the pathway order.
  4. "Reset" restores the stored evidence.

  The banner "Test value, not real data" stays visible while a test is applied.
- **Refresh:** on Live intelligence, a "Run now" button asks for the admin token in a password
  field (kept in memory only, never stored), calls `POST /api/pipeline/run`, and polls runs every
  5 s until finished.
- The replay of earlier releases stays as it is.

**Tests:** `tests/test_evidence_test.py`:
- raising a routine skill's share lowers its weight, and raising a complementing skill's share
  raises it;
- essentials are unchanged;
- stored observations are unchanged after the call;
- an unknown key gives 422.

### A4 Robustness of the evidence layer
**Goal:** no crash and no blank page; an outage shows the last good snapshot with its date.

**Files:** `src/pipeline/run.py`, `src/evidence/store.py`, `src/api/evidence.py`, `App.tsx`,
`LiveIntelligence.tsx`.

**Rules**
- **Source state:** per source, expose `last_attempt_at`, `last_attempt_status`, `last_success_at`
  and `serving_snapshot_from` (the newest stored observation's `fetched_at`). When the last attempt
  failed, screens using that source show "Showing the last good data from <date>".
- **Watchdog:** a run still `running` after `RUN_WATCHDOG_MINUTES = 45` (longer than the 30-minute
  pipeline lock, so a live run is never closed) is closed as
  `failed (interrupted)`, with a note, when runs are listed or a new run starts.
- **Lazy pages:** a failed lazy import reloads the page once (a `sessionStorage` flag), then shows
  a clear error with a reload button.
- **Remote calls:** every remote call keeps a time budget and a labelled fallback, and is recorded
  in `usage_event` (already true for OpenAI and RunPod).

**Tests:** a failing fake collector keeps earlier observations and reports the failure; the watchdog
closes a stale run; the API exposes the state fields.

### A5 Search and RunPod, measured
**Goal:** better occupation and skill search, with RunPod doing real work and the gain measured
on data we never tuned on.

**Files:** `src/occupations/detect.py`, `src/occupations/evaluate.py`, `src/intake/skill_search.py`,
`data/eval/occupation_titles_holdout.yaml` (new), `docs/RUNPOD_EVAL.md`.

**Rules**
- **Hybrid retrieval:**
  1. BM25 top `HYBRID_CANDIDATES = 50` and BGE-M3 dense top 50;
  2. fuse them by reciprocal rank fusion (`RRF_K = 60`);
  3. rerank the fused top 10 with bge-reranker-v2-m3.
- **Fallbacks:** BM25 alone when RunPod is unavailable (labelled); dense+BM25 without rerank when
  the rerank job fails (labelled).
- **Outcome (measured):** hybrid+rerank did not beat dense+rerank on the hold-out set (top-1 68%
  vs 70%) or the development set (68% vs 72%), so the app keeps dense+rerank and the hybrid stays
  in the evaluation only; skill search is unchanged for the same reason (docs/RUNPOD_EVAL.md).
- **Hold-out set:** commit it **before** any tuning. Contents: 40 new queries (at least 15 in Malay,
  5 mixed English/Malay, 5 with typos), each with the accepted O*NET-SOC codes, labelled by the
  team and dated.
- **Report:** in `docs/RUNPOD_EVAL.md`, top-1, top-3 and MRR for keyword, dense, hybrid and
  hybrid+rerank, on the old set and the hold-out set separately. The hold-out numbers are the
  ones quoted.

**Tests:** RRF ordering on a fixed example; the fallback labels; the evaluation script runs offline
with fakes.

### A6 Course and resource catalogue as a pipeline job
**Goal:** more real, checkable content, including intermediate and advanced material, collected
by the pipeline rather than typed by hand.

**Files:** `src/collectors/mslearn.py` (new), `src/pipeline/run.py`, `data/sources.yaml`,
`data/packs/gbs_fa/courses_mslearn.yaml` (generated), `scripts/review_catalogue.py`,
`scripts/check_links.py`.

**Rules**
- **Collector:** the Microsoft Learn Catalog API (`https://learn.microsoft.com/api/catalog/`, free,
  no key), modules and learning paths in English.
- **Pre-filter:** keep items whose `roles`, `products` or `subjects` relate to finance, data and
  automation: business-analyst, data-analyst, functional-consultant; power-bi, power-automate,
  excel, dynamics-finance, dynamics-365; data-analytics, finance.
- **Mapping to skills:**
  1. Embed `title + summary` with BGE-M3.
  2. Rerank each candidate against each pack skill's name and description.
  3. Keep pairs with a rerank score ≥ `CATALOGUE_MIN_RERANK = 0.5` (declared; checked by hand on
     20 pairs before use).
- **Output entries:** `level` from the API (`beginner` / `intermediate` / `advanced`),
  `minutes = duration_in_minutes`, `time_basis: reading_estimate`, `checked: <fetch date>`,
  `verified: false`.
- **`hands_on`:** true only when the item has a unit whose title starts with "Exercise".
- **Review:** `scripts/review_catalogue.py` lists candidates. A reviewer opens each one and sets
  `verified: true`. Only verified items are ever planned (Stage 0 already enforces this).
- **OpenLearn and checked YouTube and articles:** added the same way to `resources_*.yaml`.
- **Link check:** `scripts/check_links.py` checks that every course, video and article URL answers
  200 (or a redirect to the same host). It runs as a pipeline step and before the pitch, and writes
  failures to the run log.

**Tests:** the collector parses a fixture response; mapping uses fakes; unverified items are not
planned; the link checker reports a fake 404.

### A7 Visible resource-scout agent (attempt)
**Goal:** for a gap skill, an agent finds the exact part of a video or article that serves it,
shown working in an in-app window. It finds and points; it does not teach.

**Files:**
- `src/agents/{client,scout,video,article,store}.py` (new), `src/agents/character.py` (shared
  with A8), `data/agents/scout.character.yaml` (new), `src/api/agents.py`;
- `AgentWindow.tsx` (new), `typesAgents.ts`, `requirements.txt`.

**Flow**
1. **One agent, not an agent team** (§1 decision 16): a single tool-calling loop on `AGENT_MODEL`
   (`src/agents/client.py`, usage recorded); the scouts below are code tools it calls. Its voice
   and rules come from `data/agents/scout.character.yaml` (same format as A8's character file).
   Tools: `list_resources(skill)`, `video_segments(video_id, skill, level)` and
   `article_passages(url, skill, level)`. At most `AGENT_MAX_STEPS = 8` tool calls, with
   `AGENT_TIME_BUDGET_SECONDS = 45`.
2. **Video scout:**
   1. captions with timestamps from `youtube-transcript-api` (MIT);
   2. chunks of 30–90 s cut at sentence ends;
   3. RunPod rerank against "<skill name> at level <n>: <anchor sentence>";
   4. the top 3 segments; `AGENT_MODEL` writes a one-line reason per segment from the chunk text
      only;
   5. a link `https://youtu.be/<id>?t=<start seconds>`.
3. **Article scout:**
   1. fetch and extract the text with `trafilatura` (Apache-2.0);
   2. split it into passages and rerank them;
   3. code checks that each quoted passage appears in the extracted text (otherwise it is dropped);
   4. a deep link with a text fragment: `<url>#:~:text=<start>,<end>`.
4. **Scope:** only resources already in the catalogue (A6) or `resources.yaml` are scouted. No open
   web search.
5. **Pre-computing:** results for the four personas' gap skills are computed in advance and stored
   in `data/packs/gbs_fa/resources_scout.yaml`, with the date checked. YouTube often blocks caption
   requests from cloud servers, so this runs on a local machine. A live run in the demo has the time
   budget; on failure it shows the cached result, labelled.
6. **`AgentWindow`:**
   - a `Windows`-style dialog that streams steps by server-sent events from
     `GET /api/agents/runs/{run_id}/events` (steps stored in `agent_run` and `agent_step`);
   - each step shows what the agent is doing ("Reading captions", "Ranking 42 passages",
     "Checking quotes");
   - **Level 1:** a reader view of the passage with the match highlighted;
   - **Level 2 (stretch, flag `AGENT_SCREENSHOTS=1`):** Playwright screenshots of the real page with
     the passage highlighted;
   - on finish it collapses into a results card with the links.
7. **Labels:** results name `AGENT_MODEL`, the engine and the time.

**Good enough for the demo:** Level 1 completes for a cached resource in under 5 s, and a live
video run in under 45 s. Otherwise the cached result shows, labelled.

**Tests:** fake captions and pages; a quote not in the text is dropped; the step limit and budget
stop the loop; the events endpoint streams steps in order.

### A8 Progress-check agent
**Goal:** the person tells a finance practitioner what they did; the agent judges it against the
level descriptions and proposes a level, which the person accepts or declines.

**Files:** `src/agents/check.py` and `src/agents/character.py` (new),
`data/agents/progress_check.character.yaml` (new), `src/api/agents.py`, `ProgressCheck.tsx` (new),
`Overview.tsx`, `typesAgents.ts`.

**Agent setup: a character file**

The agent's character lives in a file, in the spirit of ElizaOS character files, not in code. The
model is not fine-tuned and ElizaOS itself is not used. `data/agents/progress_check.character.yaml`
holds:
- `name` and `role` ("Senior GBS finance reviewer");
- `bio`: who the character is, as a list of short lines, e.g. ten years in shared-services
  finance, has reviewed many analysts' work, plain and respectful;
- `style.all` and `style.chat`: how it speaks, e.g. one question at a time, concrete, no jargon
  without explaining it, Malaysian workplace context, never condescending;
- `adjectives`: e.g. practical, fair, precise;
- `topics`: the finance processes it can ask about (O2C, P2P, R2R, reporting, systems);
- `rules.must` and `rules.never`:
  - must: ask about real work done; ask for the tool, the frequency, the volume, the problem
    solved and who used the result; judge only against the level sentences given;
  - never: teach; give answers or hints; reveal which answer would pass; write a number; judge
    anything but the described work; comment on the person's background or identity;
- `message_examples`: 3–5 synthetic exchanges showing a good question, a follow-up on a vague
  answer, and a polite close.

**Loading and use**
- `src/agents/character.py` loads the file into a Pydantic model and fails loudly if a required
  field or rule is missing. It builds the system prompt from the file.
- At run time the prompt is joined with the retrieved context: the skill's anchors (C1), the
  role's linked O*NET tasks and the step's practice task (B4).
- Changing the character means editing the YAML, with a decision-log entry. The file is
  reader-facing, like the rest of the repo.

**Flow**
1. The agent asks 2–4 concrete questions, one at a time (what, which tool, how often, what went
   wrong, who used the result). It never teaches, gives answers or hints at what to say.
   `CHECK_MAX_QUESTIONS = 4`.
2. **Schema:** `{done: bool, next_question: str, judgements: [{level: 1..5, verdict: "yes"|"partly"|"no", quote: str}]}`.
   The model returns verdicts and quotes, never a number of its own beyond the level being judged.
3. **Code:**
   1. drops any judgement whose quote is not in the person's answers;
   2. sets `proposed_level` to the highest level L where every level from the current level + 1 up
      to L is "yes" ("partly" does not count);
   3. caps it at `current_level + 2`.
4. **Decide (C6):** accept → claim `agent_check` and a `level_changed` event; decline → nothing
   changes. If B's `record_event` (B8) is not on `main` yet, the decide route writes the claim
   only, and the event call is added during integration (§9 step 1).
5. **Limits and fallback:**
   - `CHECKS_PER_SKILL_PER_DAY = 3`;
   - with no LLM, the check is shown as unavailable (labelled), and the person can still re-rate
     themselves.
6. **Before M2:** "Check my progress" opens from Overview's next-step card. After M2 it also opens
   from each plan step (§9).

**Tests:** fake LLM:
- the character file loads; a file missing a `never` rule is refused;
- the built prompt contains every `must` and `never` rule;
- a quote missing from the answers is rejected;
- "partly" does not raise the level;
- the cap holds;
- decline changes nothing;
- accept writes the claim and the event.

### A9 Privacy, status, load test, cost
**Goal:** answer "privacy, reach, cost, freshness" with real features and measured numbers.

**Files:**
- `src/privacy.py` (new), `src/api/privacy.py`, `src/api/status.py`, `src/pipeline/run.py`;
- `Privacy.tsx`, `Status.tsx`, `ResumeCode.tsx` (new);
- `scripts/load/locustfile.py`, `scripts/cost.py`;
- `docs/LOAD_TEST.md`, `docs/COST.md`.

**Privacy**
- **Endpoints:**
  - `GET /api/profiles/{id}/export` returns every stored row for the profile;
  - `DELETE /api/profiles/{id}` deletes the profile row and every row in any table with a
    `profile_id` column (found from `metadata.tables`).
- **Retention:** `PROFILE_RETENTION_DAYS = 90`; the pipeline deletes profiles not updated for that
  long.
- **Resume code:** the profile id as text and QR (npm `qrcode`, MIT), with copy and paste to
  continue on another device.
- **Privacy page:** maps the PDPA's seven principles (General, Notice and Choice, Disclosure,
  Security, Retention, Data Integrity, Access) to what the app does:
  - PII stripped before any model;
  - no name, contact or CV text stored;
  - anonymous id;
  - export, delete, retention;
  - what goes to OpenAI and RunPod.

  It states that the app is a prototype, not a PDPA compliance certification.
- **Consent wording** (B places it in onboarding, word for word): "Qart.ai keeps only what matching
  needs: your situation, current role, skill levels with the CV sentence behind each, hours,
  budget and interests. Names, IC numbers, phone numbers and emails are removed before anything
  reads your CV, and the CV text is not stored. Your profile opens only with the private code kept
  in this browser. You can export or delete it at any time; profiles unused for 90 days are
  deleted."

**Status page (C9):** freshness, runs, fallbacks, usage and cost, the fairness result (C10), and
platform SDG totals (C4, suppressed below 5). Add the "Status" link to the Sidebar's Evidence group
in the same commit as the page, and a "Privacy" link in the Sidebar footer with the Privacy page.

**Load test** (`scripts/load/locustfile.py`, Locust, MIT)
- **Journey:** `POST /profiles` with a persona's levels (no CV parsing), then `/matches`,
  `/pathway`, `/tracks`, `/sdg`, `/api/forecast` and `/api/trends`.
- **Paid calls:** 5% of virtual users also run `/intake/parse` on a sample CV (real LLM, capped at
  `LOAD_MAX_LLM_CALLS = 50` per run).
- **Steps:** 25, 50 and 100 users, 5 minutes each, against the deployed URL, run from a laptop.
- **When:** a first run before M2 skips endpoints that do not exist yet (`/sdg`); the recorded run
  is after M2 (§9 step 4).
- **Scope:** the load test is the only concurrency proof; no simulated AI users (§1 decision 16).
- **Results** in `docs/LOAD_TEST.md`: p50 and p95 per endpoint, error rate, requests per second,
  fallback counts, and the date and commit.

**Cost** (`scripts/cost.py`)
- Reads `usage.totals`. The prices are declared parameters with source and date: OpenAI per-token
  prices for both models, RunPod per-second price, Replit plan.
- Output in `docs/COST.md`, with measured and projected values in separate tables:
  - measured cost per journey and per month;
  - projected cost at 1,000 and 10,000 users per month, with the ringgit rate's source and date.

**Tests:** delete removes rows from every `profile_id` table; export returns them; retention deletes
only idle profiles; the status shape matches C9.

### A10 Compare futures
**Goal:** stage 6 shows the shift between scenarios clearly.

**Files:** `Future.tsx`, `typesAgents.ts`. No backend change: it uses `/matches` and
`/sensitivity`.

**Compare futures**
- Moderate and fast side by side from `/matches?scenario=...` (C2), with rank-shift arrows and
  each skill's weight before → after for the chosen role.
- The sensitivity ranks from `/sensitivity` as a small table (intensities 0 to 1.5).
- Labelled estimates, with the scenario parameters shown (`SCENARIO_INTENSITY`, horizon).
- The existing "Today → Future you" content on this page stays; compare futures is added to it.

**Tests:** `tsc`, lint, build; a manual check with Nur and Kavitha that the arrows match the two
`/matches` responses.

**Out of scope:** "stay and adapt" (§1 decision 16).

---

## 8. Branch B: scoring and pathway (Meiirman)

Stage 1 (before M1) = B1–B4.

### B1 Correctness fixes
**Goal:** the numbers a judge checks first are right.

**Files:** `src/match/engine.py`, `src/intake/extract.py`, `src/pathway/tracks.py`,
`src/params.py` (B), `data/samples/kavitha.txt` (new), tests.

**Rules**
- **Scenario floor:** `factor = max(SCENARIO_FACTOR_FLOOR, 1 + d·s·a)`, with
  `SCENARIO_FACTOR_FLOOR = 0.1` (declared: a skill can lose most of its weight but never vanish or
  go negative, even at the 1.5 sensitivity intensity).
- **ERP backstop:** after the LLM, if the scrubbed CV names an ERP system (`ERP_ALIASES` in
  `params.py`: SAP, S/4HANA, Oracle, Dynamics 365, NetSuite, Workday Financials, Infor, Sage X3,
  SQL Accounting, AutoCount) and no `erp` claim exists, add one at level 2 with that sentence as
  evidence and `source: "cv"`. The note says "added by rule". The same applies in the keyword
  fallback.
- **Totals:** one definition only.
  - Plan hours = the planned study steps.
  - AI-basics hours are shown separately as "+ X h AI basics", never added silently.
  - The with-AI comparison names both parts.
  - Likely source of the 6.2 h versus 8.5 h mismatch: `comparison()` adds AI basics, the plan
    total does not. Confirm it with the CV that showed it.
- **Thin profile and unknown skill:**
  - every skip in onboarding still gives ranked roles, fit 0 with a range, and a plan;
  - an unknown skill in a request gives 422 with its name;
  - a CV phrase that matches no skill is listed as "not in our skill list", never dropped silently.
- **Kavitha:** add her synthetic CV now, so both branches can demo her:
  - 9 years; senior reporting analyst at a GBS centre;
  - Power Automate flows for invoice intake;
  - Python scripts for reconciliations;
  - S/4HANA migration UAT;
  - multi-source Power BI with Power Query;
  - trains new analysts.

  Labelled synthetic like the others, and added to `SAMPLES`.

**Tests:**
- weights > 0 at every intensity in `SENSITIVITY_INTENSITIES`;
- essentials are unchanged;
- the ERP alias adds a claim with its sentence;
- the plan total equals the sum of its steps;
- a thin profile returns roles and a plan.

### B2 Level scale 0–5 and the level descriptions (C1)
**Goal:** levels mean something observable, and the person picks a sentence, not a number.

**Files:**
- `src/levels.py` (new), `data/packs/gbs_fa/levels.yaml` (new);
- `src/params.py` (`PROFICIENCY_LABELS`), `src/journey/store.py` (`MAX_LEVEL = 5`);
- `src/intake/extract.py` (`LEVEL_GUIDE`, schema enum 1–5), `src/goal/posting.py` (level enum 1–5);
- `src/api/journey.py` (`/pack`), `LevelPicker.tsx` (new), `Onboarding.tsx`, `Roles.tsx`,
  `typesScoring.ts`.

**Rules**
- **Anchors:** five per skill for every skill any destination role requires. `python -m src.levels --missing`
  lists the gaps.
- **Basis:** start from the team's research (SkillsFuture Accountancy job tasks, SFIA skill
  levels, University of Florida AP competency), write our own sentences, cite the basis, and review
  with the team.
- **Extraction:** the prompt's level guide uses the scale meanings, plus the skill's anchors when
  short enough (otherwise the meanings only).
- **`LevelPicker`:** shows the skill's sentences from 1 to 5. The person picks the highest true one;
  "None of these" = 0; "Not sure" = unstated. The CV line shows beside it when one exists.
- **Existing claims:** keep their numbers (§1 decision 2). Bump `CALCULATION_VERSION` to
  `journey-3` and log it.

**Tests:**
- every required skill has anchors 1–5;
- the API exposes six labels;
- a stored level-4 claim still loads;
- the extraction schema accepts 5.

### B3 Fit range, band, components, what would raise it (C2)
**Goal:** "why this score, and what would raise it" is answered on screen in one click.

**Files:** `src/match/decision.py`, `src/api/journey.py`, `src/params.py` (B), `ScoreWhy.tsx`
(new), `Roles.tsx`, `typesScoring.ts`.

**Rules**
- Implement C2 exactly, with `BAND_THRESHOLDS = {"strong": 75, "good": 55, "fair": 35}`.
- **Pay (C11):** each role card shows the group's median monthly pay, with the national median
  beside it, the year and source, its "observed" tag and the note "pay of all employees in this
  occupation group, not an offer for this role". Its "Why?" shows the published row. Pay is never
  used in fit, band or rank. Until A's pay series is on `main`, the card shows "not published"
  (the field is `null`). Test with fixture observations.
- **Score chip:** each role card shows a large chip: band, `fit`, range ("Fair · 41 (32–48)").
  Its "Why?" opens `ScoreWhy`.
- **`ScoreWhy` panes:**
  1. **The formula** with the person's own numbers:
     `fit = 100 × Σ w·min(c/r, 1) ÷ Σ w`, a row per requirement (weight, claimed, required, points),
     and evidence quote or "self-rated" per claim.
  2. **Why each weight is what it is:** the existing `shift_reason`, with its source and period.
  3. **What would raise it:** C2 `raise`, each with its route (study, practice, check).
  4. **Essentials still short:** always visible.
  5. **Labels:** the band thresholds are an assumption; the range basis.

**Tests:**
- the range for a fully evidenced profile has low = fit with unstated 0;
- unevidenced claims lower `low`;
- `raise` points equal a re-score;
- the band follows the thresholds.

### B4 Study versus practice (C3)
**Goal:** plans are honest about what study can do; level 3 comes from work.

**Files:** `src/pathway/planner.py`, `src/pathway/practice.py` (new),
`data/packs/gbs_fa/practice.yaml` (new), `src/pathway/tracks.py`, `src/api/journey.py`,
`src/journey/progress.py`, `src/params.py` (B), `TrackMap.tsx`, `Pathway.tsx`, `typesScoring.ts`.

**Parameters** (B section, each with basis)
- `STUDY_MAX_LEVEL = 2`: study alone reaches "aware" at most (MQF counts 40 notional hours per
  credit including practice; vendors expect months of use).
- `LEVEL1_MIN_HOURS = 1`.
- `LEVEL2_MIN_HOURS = 20` of material covering the skill, including at least one `hands_on` item
  (the shortest recognised programme found was 19 h: WSQ Vendor Performance Management).

These replace `COURSE_LEVEL_REACH`, `COURSE_MAX_GAIN_*` and `COURSE_SHORT_MINUTES` in the planner.
Remove the old ones with a decision-log entry.

**`practice.yaml`**
- Per skill: tasks for 2→3 and 3→4, each with `text`, `weeks_low`, `weeks_high`, `basis` (title,
  url, read) and `show_by` (what the person describes in the progress check).
- Practice tasks are suggestions to agree with a manager, not courses; their weeks are estimates.

**Planner**
1. Order gaps as today: essentials first, then by weight.
2. Study steps: add verified courses covering the skill, shortest first, until the level rule is
   met or the courses run out. Respect prerequisites.
3. If the required level is 3 or more, add one practice step per level above 2.
4. Plan time:
   - study hours at the person's weekly hours;
   - practice weeks in sequence after the study steps for that skill, shown as a range.
5. `fit_after_study` uses levels after study; `fit_after_practice` assumes the practice targets
   are reached. Both are ranges by the C2 rule (planned levels count as unevidenced).

**Unlocking**
- A study step unlocks when the step before it is done (as today).
- A practice step unlocks when that skill's study steps are done.
- A practice step is complete when the skill's claim reaches its target, through an accepted
  progress check (`agent_check`) or a self re-rate (labelled "self-rated").
- "Continue anyway" marks it `skipped` (C5), labelled.

**Tests:**
- study never takes a skill above 2;
- 20 h without hands-on material stays at 1;
- practice steps appear only for levels above 2;
- totals and ranges are consistent;
- unlocking follows the rules, using fixture `agent_check` claims (A8 is not needed for this test).

### B5 The plan adapts to the person
**Goal:** an experienced person does not get beginner content; a beginner gets the basics first.

**Files:** `src/pathway/tracks.py`, `src/pathway/planner.py`, `src/params.py` (B), `Pathway.tsx`.

**Rules**
- **AI basics:** skipped when any of `prompt_engineering`, `process_automation`,
  `advanced_technology_integration` or `data_management` is claimed at level 3 or above with
  evidence (`cv` or `agent_check`). Set `AI_BASICS_SKIP_LEVEL = 3`.
  - The plan says why ("Skipped: your CV shows ‘<quote>’") and offers "Show AI basics anyway".
  - Students and switchers always see AI basics.
- **Course level:** no `beginner` course for a skill claimed at 2 or above. A skill at or above
  `STUDY_MAX_LEVEL` goes straight to practice.
- **Show the reason:** every adaptation is visible as a short "Adjusted for you" note with its rule.

**Tests:** Kavitha has no AI basics and no beginner courses; Hafiz has AI basics first; removing
Kavitha's evidence brings AI basics back.

### B6 Personas and the journey test
**Goal:** different people get visibly different results; this is the proof that nothing is
hard-coded.

**Files:** `data/samples/*.txt`, `src/api/journey.py` (`SAMPLES`), `tests/test_personas.py` (new).

**Rules**
- **Four personas:** Hafiz (graduate), Mei (switcher), Nur (working, at risk), Kavitha (working,
  advanced). Each CV is labelled synthetic.
- **The test** builds each profile through the API from fixed levels (no LLM) and asserts:
  - top roles differ between at least three personas;
  - Kavitha's top-role fit exceeds Nur's;
  - AI basics are shown for Hafiz and not for Kavitha;
  - Kavitha's plan has practice steps and no beginner courses;
  - every persona's response has no number without a source or a label in C2 and C3.

### B7 SDG mapping and heatmap (C4)
**Goal:** the SDG link is specific, explained and changes what a person can compare.

**Files:** `data/packs/gbs_fa/sdg.yaml`, `src/pack.py` (`SdgMap`), `src/pathway/sdg.py` (new),
`src/api/sdg.py`, `SdgHeatmap.tsx` (new), `Pathway.tsx`, `Roles.tsx`, `typesScoring.ts`.

**Mapping**
- `sdg.yaml` gains:
  - `skills: {skill_id: [{target, how, source}]}`;
  - `roles: {role_id: [{target, how, source}]}`.

  Keep `skill_kinds` as the fallback.
- **Pack check:** every skill and destination role has at least one link, every link has a
  one-line `how`, and every target is in `targets`.
- **Targets:** 4.3, 4.4, 8.2, 8.5 and 12.6 (already defined). Add others only with a written
  mechanism and source.

**Hours**
- A study step's hours are split equally over the skills it raises.
- A skill's hours count toward every target it serves.
- Practice steps show as a marker, not hours.
- The path-level links (4.3 for free learning, 8.5 for the destination move) appear as
  `path_links`.

**Heatmap**
- On `/pathway#sdg`: rows are the plan's skills, columns are targets; a cell is planned study hours.
- One sequential hue, with values printed in cells and a table view (dataviz rules).
- A click on a cell opens the reasons and sources in `Windows`. The totals row is labelled "not
  additive across targets".
- **Roles view:** on `/roles`, a compact roles × targets grid (linked or not, with the reason on
  click), so roles can be compared by contribution.

**Tests:** every skill and role is linked; cell hours equal the step split; totals equal the column
sums; the API shape matches C4.

### B8 Progress events and badges (C5)
**Goal:** progress is tracked from real events, and badges reward only what happened.

**Files:** `src/journey/events.py` (new), `src/journey/progress.py`, `src/api/decision.py`,
`src/api/badges.py`, `Badges.tsx` (new), `Pathway.tsx`, `typesScoring.ts`.

**Rules**
- **Events:** write `journey_event` rows from the progress, destination and profile routes, and
  expose `record_event` for A8.
- **Badges** (each derived only from events):
  - "First step" (first `course_done`);
  - "Skill up" (each `level_changed` that increases a required skill);
  - "Essentials ready" (all essentials of the destination at their level);
  - "Halfway" (half the study hours done);
  - "Plan complete".
- **Display:** a `Badges` strip on the plan page, each badge with the event that earned it and its
  date.

**Tests:** no event, no badge; undoing a course does not keep "Halfway" if no longer true;
`level_changed` from `agent_check` earns "Skill up".

### B9 Report figures and the fairness function
**Goal:** the Section 4 numbers come from code, not prose.

**Files:** `scripts/kpis.py` (new), `src/match/fairness.py` (new), `docs/KPI_RESULTS.md` (generated).

**`scripts/kpis.py` computes:**
- verified free-course coverage of the required skills, using the Phase 1 denominator (27/37 at
  73%, target ≥ 90%), with catalogue changes disclosed separately;
- the free share of each persona's plan;
- the share of displayed numbers in the C2 and C3 responses that carry a source or a label.

**Fairness:** `paired_profile_check` (C10), sharing its pairs with `tests/test_fairness.py`.

### B10 More GBS finance roles
**Goal:** more, and more specific, destination roles. Every one is traceable to the TalentCorp
study and fully wired (requirements, tasks, evidence, levels, practice, SDG, courses), so
suggestions are never generic.

**When:** after B7 (it needs the levels, practice and SDG formats), before M2.

**Files:** `data/packs/gbs_fa/{roles,skills,tasks,field,levels,practice,sdg}.yaml`,
`src/collectors/talentcorp.py` extraction data if a page is newly cited (ask A first: it is A's
code), tests.

**Rules**
1. **Candidates:** every finance-and-accounting role in TalentCorp (2024), *Impact Study of AI,
   Digital and Green Economy: GBS*, that is not yet a destination role and has a skill list in the
   study. That includes the emerging roles it names and the medium- or low-impact roles the study
   gives as transitions from current roles. List them with their pages in the commit body before
   adding any.
2. **A role is added only when all of these exist:**
   - its title and impact level, with page;
   - its requirements from the study's skill lists, with pages, tiers and at least one essential;
   - an O*NET-SOC code from the ESCO–O*NET crosswalk in `field.yaml`;
   - O*NET tasks linked to its skills in `tasks.yaml`;
   - SDG links with reasons;
   - level anchors and practice tasks for any new skill.

   A role missing any of these is not added; it is listed in `docs/decision_log.md` with the
   reason.
3. **New skills:** only ones the study names (with page). A new skill without a verified course
   stays "no verified free course yet". A's catalogue (A6) is asked to cover it, never filled with
   a guess.
4. **Current roles:** if the study gives a current role new transitions, add them with pages.
5. **After adding:** `load_pack()` checks pass; the persona test (B6) still shows different
   results; the occupation evidence for new SOC codes arrives in the next pipeline run (no code
   change); `scripts/kpis.py` re-reports coverage, keeping the Phase 1 denominator and showing new
   skills separately.

**Tests:** the pack check rejects a role missing a page, an essential, a SOC code or an SDG link;
each new role appears in `/matches` with components, pay (when published) and an SDG row.

---

## 9. Integration on `main` after M2

1. Mount A's `AgentWindow` ("Find the best part") and `ProgressCheck` ("Check my progress") on
   each node of B's `TrackMap`. Practice steps use `ProgressCheck` to complete. The progress
   check's decide route calls `record_event` if it does not yet.
2. Overview reads the real C2–C5 fields; remove the fixtures.
3. Confirm that the Sidebar's "5 SDG contribution" link reaches `/pathway#sdg`.
4. Run the full journey with the four personas, the load test, the link check, `scripts/kpis.py`
   and `scripts/cost.py`. Record the outputs.
5. Update `docs/explain/*`, `README.md`, the declaration log and the decision log.

---

## 10. UI phase (last, after M2 and integration)

The redesign comes after all features work, so it is done once, on the final set of screens.
Most sections stay; the phase removes, changes and restyles.

1. **Walkthrough:** the owner (Moo7x) opens the integrated app and goes page by page. For each
   page, he states what to remove, what to change, and an example of how it should look
   (screenshots or references).
2. **Spec:** the walkthrough is written into this section as a table per page (item, change,
   owner), plus a global style part (colours, type, spacing, buttons, cards) with its tokens. It is
   committed on `main` before any UI code.
3. **Global style first (A):** tokens and shared classes in `index.css`, plus the Sidebar.
   Committed and pushed so both branches build on it.
4. **Pages by owner:** both work on fresh branches from `main` (`ui-a`, `ui-b`) with the same file
   ownership (§5) and the same merge order (B first). A page item never moves to the other owner.
5. **Rules:**
   - The redesign never removes a must-have from §0, a source, a date, a label or a "Why?" panel.
   - No new numbers.
   - Mobile at 375 px and keyboard focus are checked on every page.
   - Dataviz rules apply to every chart.

---

## 11. Measuring against the Phase 1 targets (both, after the UI phase)

No branch work package; this runs on the finished app.

**User test** (`docs/USER_TEST.md`)
- **Participants:** 10 or more classmates, each given one persona card (synthetic data only), on
  the deployed app.
- **Time:** from "Start" to seeing ranked roles **and** a pathway (target: 80% under 5 minutes).
- **Understanding:** then ask, without help, "Why was your top role recommended?". A pass names at
  least two of: a matched skill, a gap, the score's components or the evidence behind a weight
  (target: 70%).
- **Records:** times, pass or fail, persona, date and app commit. No names or personal data.

**Other targets**
- **Coverage and traceability:** from `scripts/kpis.py` (B9).
- **Freshness, cost, load:** from the status page, `docs/COST.md` and `docs/LOAD_TEST.md` (A9).

---

## 12. Report Section 4 and Q&A: where each answer comes from

Reference for the submission work after the UI phase (§1 decision 15). It shows which feature
answers which requirement; it is not a work package.

| Requirement | Evidence | Owner |
|---|---|---|
| Reach and channel | Report text: university and TVET career centres first (QR to the app, resume codes), then employers' L&D; numbers with their reasoning | Moo7x |
| Data freshness | Status page, run history, schedule | A |
| Cost per user / month | `docs/COST.md`, `usage_event`, load test | A |
| Learning cost | `free_share`, `scripts/kpis.py`; HRD Corp: none verified, said openly | B |
| SDG impact against Phase 1 | `docs/KPI_RESULTS.md`, `docs/USER_TEST.md`, platform SDG totals | both |
| Privacy (PDPA) | Privacy page, export, delete, retention, PII stripping | A |
| Fairness | `paired_profile_check` on the status page | B |
| 4.1 proof | Fit formula with the floor, study / practice rule, forecast backtest table, load-test log | both |

| Q&A question | Answer on screen | Who answers |
|---|---|---|
| Change the trend data now. What should change? | Change test (A3), replay | Moo7x |
| Where does this come from? Is this course or number real? | "Why?" panels, link check, `verified` catalogue | Meiirman |
| Why this score, and what would raise it? | `ScoreWhy` (B3) | Meiirman |
| How is the data kept current, and what does it cost? | Status page, `docs/COST.md` (A9) | Moo7x |
| What if AI moves faster or slower? | Compare futures, sensitivity (A10) | Meiirman |
| How do you stop invented jobs or courses? | Pack and verified catalogue only, quote checks, `verified: false` never planned, the model never writes numbers | Moo7x |

---

## 13. Definition of done (every work package)

- Works through the real API on a local build with the four personas, not only with mocks.
  Frontend types match the server models.
- Every number shown is labelled observed (source and date), assumption or estimate. Missing shows
  "not stated", never 0.
- New parameters are named and commented (what, why this value, which kind) and logged in
  `docs/decision_log.md`.
- Tests cover the rule and its edge cases. All checks are green.
- Commits are small. `docs/explain/<module>.md` is updated. New libraries and models are declared.
- **Nothing outside the package:**
  - no renamed fields;
  - no formula changes outside the package;
  - no edits to the other owner's files;
  - no invented data;
  - no removed features.
