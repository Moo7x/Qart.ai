# Qart.ai — product and system design

Version of 23 Oct 2026. Built from the Domain 1 brief (problem, users, journey, six must-haves,
good-to-haves, rules, success test, preliminary rubric), the participant handbook (deliverables),
the team's analysis, design reviews, and data sources verified live on 23 Oct 2026.
Agreed: name Qart.ai; demo field Malaysian GBS finance & accounting; a visible on-screen AI agent
that acts for the user (opens tabs, navigates, highlights, explains), inspired by Burrow (§4.9). It
researches and shows; it never tutors, hints at answers or grades. Agent look: a simple Qart icon;
voice off by default, one click to turn on.

## 0. Constraints from the brief and handbook
- Problem: continuously track AI advancement → predict emerging/declining skills and jobs → match
  today's workforce and tomorrow's talent to future roles → personalised reskilling pathways → show how
  each role and skill connects to the SDGs.
- SDGs to make unmistakable: 4.4 (relevant skills for decent jobs), 4.3 (lifelong technical and
  vocational learning), 8.2 (productivity through innovation), 8.5 (full and productive employment).
  Relevant: 5, 9, 10.
- Six must-haves: profile intake (CV/form/questionnaire) · updatable AI/job-market signal layer with
  source + date (no hard-coded lists) · ranked roles with explainable match score + skills gap ·
  ordered pathway with time, free/low-cost resources (HRD Corp-claimable etc.) · every role and skill
  tagged to ≥1 SDG + how the chosen path contributes · more than one future scenario, labelled as
  estimates.
- Success test: new user → ranked roles + actionable pathway in minutes; every recommendation shows its
  source; output visibly changes when trend data changes; SDG link meaningful, not decorative.
- Rules: public/open/synthetic data only (no real CVs); name the LLM; cite every recommendation; never
  invent jobs, courses or statistics; AI supports, humans decide.
- Preliminary rubric: Innovation 30 (specific user + moment of need; original mechanism from signals to
  forecasts to decisions) · Problem-solution fit 25 · Feasibility 25 (live trend layer feeding role
  matching; hardest risk + fallback) · Clarity 20.
- Deliverables: PRD (official template), pitch deck, live link, Technical & Tools Declaration, GitHub
  repo (continuous history, committee access), 5–7 min video.

## 1. Product
**Name:** Qart.ai.
**Promise:** from "who I am today" to "where I can be in the AI era", for people in Malaysia, with
evidence that keeps updating as AI and the job market move, and a visible AI agent that researches the
user's field, shows what changed and acts on screen (opens the evidence, courses and real job openings)
while the person makes the decisions.
**Original mechanism (Innovation):** field-aware research agent → validated, dated evidence → task-level
change → skill emphasis per scenario → personal ranking and pathway → every change traceable back to
its evidence, shown on screen by the agent.

**Users (one engine, tailored by the first intake question):**
| Situation | Tailoring |
|---|---|
| Working adult at risk | "What is changing in my current job" panel; reskilling pathway; adjacent roles |
| Fresh graduate / student (also used by TVET & university career centres) | no current-job panel; entry roles; skill-building pathway; entry-level job links |
| Career switcher | transferable skills from the old field; switch pathway |
| HR / L&D manager | upload a team of synthetic CVs → workforce skills-gap heatmap + team reskilling plan (aggregate only) |

**Demo field:** first field with verified depth = Malaysian Global Business
Services (GBS), finance & accounting function: TalentCorp's Malaysian study assesses 80 GBS roles
(18 highly, 49 medium, 8 low impacted by AI/digital/green), names 5 emerging roles and 16 in-demand
skills, documents career pathways with upskilling skills and covers ESG/green (2024, verified 23 Oct).
Engine and data model are field-agnostic. **Coverage levels:** *deep* for the curated GBS finance
pack (verified roles, tasks, essentials, courses, SDG mappings); *basic* for any other field — built
automatically from O*NET/ESCO occupations and skills, Economic Index task use and the research agent's
findings for that field, with fewer verified courses, labelled "basic coverage" on every screen. More
deep packs can be added later.

## 2. User journey (screens)
1. **Tell us about yourself:** situation → upload a synthetic CV (PDF/DOCX/text; samples provided) or
   form/short questionnaire → extracted skills, experience, current tasks, interests, weekly hours,
   budget, language → editable profile. Personal identifiers removed before matching.
2. **Future Skills Radar:** skills, tasks and roles in the user's field labelled rising / changing /
   stable / weakening / insufficient evidence, each with metric, period, geography, source + date and
   strength; radar chart + trend sparklines; source drawer with the actual row/passage.
3. **Get matched:** ranked real roles; match score with its parts; skills gap in 3 columns (ready now /
   bridgeable / missing); outlook per scenario; compare two roles; "see real openings" links.
4. **Follow a pathway:** ordered, week-by-week, hours per step, free / low-cost / HRD Corp-claimable
   (only when verified); each step names the skill it closes and its SDG target with "how this
   contributes"; person-level SDG contribution summary.
5. **Today → Future you:** a clean side-by-side view at the end of the journey — current role and
   skills vs the chosen future role after the pathway (skills gained, fit before/after under each
   scenario, hours, cost, SDG targets your path contributes to).
6. **What changed:** before/after of radar, ranking and pathway when new evidence arrives, with the
   evidence → task change → skill weight → score → step chain for each change.
7. **Live intelligence page:** animated n8n-style canvas of the pipeline (sources → research → fetch →
   validate → map → measure → forecast → match → notify), run history, source registry with credibility
   tier and terms, stale/fallback states, agent findings and review queue.
8. **HR view:** team heatmap (skills × roles), team pathway; groups < 5 suppressed.
Across all screens: the on-screen agent (§4.9). Extras from the good-to-haves: automatic re-planning,
EN/BM interface (中文 later), mobile layout, fairness check, Telegram notification on changes.

## 3. Evidence (what each source proves)
| Family | Source | Proves | Does not prove |
|---|---|---|---|
| Malaysian labour | OpenDOSM API `wages_occupation` (employees + wages by occupation group, annual; 2010 excluded: classification break), `lfs_month`, `lfs_month_youth`, `employment_sector` | shifts between occupation groups: clerical share 14.52% (2011) → 13.10% (2025) while clerical headcount still grew 1,109k → 1,360k; professionals 13.85% → 18.74% (recomputed 23 Oct) | demand for one job title or skill |
| Malaysian job ads | DOSM "Big Data Analytics: Job Market Insights" quarterly releases (online job-ad offerings by occupation; e.g. Accountants & auditors 20,111 / 587,801 = 3.42% Q4 2025 → 24,784 / 626,861 = 3.95% Q1 2026 → 22,067 / 555,509 = 3.97% Q2 2026; published 25 May, 25 Jun, 18 Aug 2026) | advertised demand by occupation, counts and shares per quarter | a vacancy census; AI causality; demand for one task; a long-run trend (3 quarters, one lineage, comparability to check) |
| Malaysian role impact | TalentCorp GBS study (2024) + MyCOL critical occupations | expert-validated impact per role, emerging roles, in-demand skills, pathways | live trend, vacancy counts |
| AI task use | Anthropic Economic Index (country data from 2025-09; detailed MY cells publish `pct` only; 2026-06 sampling changed) | which tasks people use AI for; change between compatible releases | hiring demand |
| Employer examples | public job APIs (Remotive: attribution, 24 h delay, low polling; Arbeitnow) — global, labelled; agent-found Malaysian employer evidence | which skills employers currently ask for | Malaysian demand by themselves |
| Reported deployment | agent-found company/news/employer statements (e.g. a Malaysian GBS centre announcing AI for invoice matching), each with cited passage | that an organisation reports using AI for a task | how widespread it is; job losses |
| Potential exposure | ILO generative-AI occupational exposure (2025 update; licence checked before use) | which tasks/occupations could be affected | that they are affected; job losses |
| Leading signals | arXiv (cs.AI/CL/LG), Hacker News "Who is hiring", GDELT news (Malaysia) | early movement in capabilities and attention | labour demand |
| Taxonomy | ESCO API, O*NET 31.0 | tasks, skills, wording | AI exposure |
Every observation: source, metric, unit, denominator, geography, entity, period, published date,
fetched date, value or claim, URL, cited span, hash, licence, method version. Missing ≠ 0.

## 4. System design
### 4.1 Continuous intelligence loop (n8n-style, in plain Python)
Scheduler (Replit Scheduled Deployment runs the pipeline command; "Run now" runs the same code; DB run
lock; bounded retries) → collectors + research agent → validation → evidence store → task/skill/role
recomputation → each user's matches and pathway proposals → change records → notifications (in-app,
on-screen agent, Telegram). Every run, including "no change", is logged and shown. Plain Python
(no n8n/LangGraph framework; their ideas are implemented directly).

### 4.2 Research agent (field-aware, finds information itself, keeps working)
Tool-calling agent (gpt-4o-mini) with field profiles ("character files", YAML: field, roles, tasks,
keywords, ESCO/O*NET codes, allowed source types, cadence) and a rules file (cite everything, never
produce numbers itself, respect rate limits and terms, prefer primary sources).
Workflow, run by the scheduler and whenever a new user's field arrives:
1. **Research questions** from the field profile and users' profiles (e.g. "is AI changing invoice-
   matching tasks?", "which reporting skills do Malaysian GBS employers ask for now?").
2. **Discovery/search** with tools: arXiv, HN, GDELT (MY), job APIs, ESCO, Economic Index rows, and web
   search restricted to the source TYPES the rules allow (government statistics, official reports,
   company newsrooms, research papers, job boards with open APIs).
3. **Retrieve** the supporting passage/table (URL, dates, hash stored).
4. **Check** provenance, relevance to a role/task/skill, duplication (same underlying data = one
   lineage) and contradiction with existing evidence; a contradiction opens an investigation (search
   for a third lineage, record both sides).
5. **Extract** structured evidence (entity, claim or metric, direction, period, geography) with the
   cited span; the claim-to-passage check rejects anything the passage does not support.
6. **Publish automatically** when the checks pass. A NEW source is added to the registry by the agent
   itself when it meets the rules: allowed source type, terms permit the use, and a credibility score
   (rubric: authority, directness, transparency, freshness, coverage, reproducibility, minus
   noise penalty; provisional) at or above tier B. **Nothing waits for a human:** an ambiguous case
   (tier C/D, unclear terms, changed methodology/schema, unresolved contradiction) is automatically
   **quarantined as an "unconfirmed signal"** — stored and shown, never used in scores — and the agent
   itself searches for an independent second lineage; it is promoted automatically when corroborated.
   An admin override exists but is never required.
   **Scope-aware conflicts:** two claims about different countries, periods, populations or
   measures are a scope mismatch, not a contradiction (employment can grow while job ads fall); a
   repeated article is not independent corroboration; conflicts are never resolved by majority vote.
   **Decision-focused research:** the research queue is prioritised by how much an
   uncertainty affects users' chosen roles and pathway steps (from the what-if engine, §4.5),
   evidence weakness, missing coverage, relevance and fetch cost (declared heuristic, not a
   calibrated probability).
7. **Update** affected task-change labels, skill weights, role outlooks, users' matches and pathway
   proposals; write change records naming the evidence; notify.
The agent never writes scores; code recomputes them from the evidence it published.

### 4.3 Prediction: signal → trend → forecast, down to tasks and skills (central mechanism)
Signal = one observation; trend = persistent, corroborated pattern; forecast = conditional estimate
under a scenario. Every supported role has a **task model**:
1. **Tasks of the role:** TalentCorp role description (Malaysian) crosswalked to O*NET task statements
   and ESCO skills (explicit, reviewed crosswalk table).
2. **Task-change evidence** per task, kept as FOUR separate kinds, never merged or relabelled:
   - **observed AI use** — Economic Index `pct` (global; MY where published), change between
     compatible releases, global automation-vs-augmentation pattern of that use;
   - **reported deployment** — agent-found statements that organisations use AI for the task;
   - **potential exposure** — ILO exposure estimate for the task/occupation;
   - **expert impact** — TalentCorp impact level and in-demand skills, with the DRIVER the study states
     (AI, digital or green economy; not every impact is attributed to AI).
   Each task shows these four facts side by side with sources and dates; there is no "being automated"
   verdict from usage alone. A short summary line uses only supported wording ("AI use of this task
   is rising in sampled conversations; one Malaysian employer reports deploying it").
3. **Requirements = essentials + emphasis.** Each role has (a) **essential skills, prerequisites and
   qualifications** with a required level that NO scenario lowers (e.g. financial accounting
   knowledge stays essential even when AI does the calculations); (b) **emphasis weights** over its
   responsibilities, which scenarios may shift (e.g. more weight on interpreting and reviewing results,
   on exception handling and on AI-tool use, when the scenario assumes more AI assistance on a task).
   Shift rules are declared, shown, and cite the task evidence that motivates them.
4. **Role demand outlook** (kept separate from skills): role → MASCO group → DOSM share trend with
   backtest + TalentCorp emerging/in-demand status + MyCOL shortage listing; shown as evidence.
5. **Forecast under a scenario** (§4.4): assumed task changes within the 2-year horizon → new
   emphasis weights (essentials unchanged) → role requirements → this person's fit, gap and pathway.
   Every step labels what is OBSERVED (with source) and what is ASSUMED (scenario rule).
6. **Backtests:** DOSM trend vs naive baselines (train ≤ 2021, test 2022–2025, error reported) —
   validates the employment-share projection only. A check against a later Economic Index release
   validates an AI-USE forecast only, never workplace automation or employment outcomes.
7. **Keeps learning as data grows:** when a run brings NEW data, the trend models are refitted on all
   data so far, backtests re-scored, and each model version stored with its error; the Live
   intelligence page shows forecast error over time and what the newest data changed. A run with no
   new data keeps the model unchanged and says so (no claimed improvement).
Every radar item, role card and pathway step links back through evidence → task change → skill
weight → score → step, so "why?" always has a traceable answer.

### 4.4 Scenarios (must-have 6)
Moderate vs Fast AI adoption, 2-year product horizon, declared assumptions per task type (which
automation-/augmentation-labelled tasks change by the horizon). Scenario → task changes → skill
emphasis → role requirements → fit and outlook. The toggle never changes the person's own skills.
Every change shows its assumption and evidence. Labelled "estimate, not a prediction".

### 4.5 Matching (must-have 3)
- **Every supported role is scored** (small catalogue): semantic retrieval (BGE-M3 on RunPod; BM25
  fallback) only maps the person's free text to canonical skills — it never removes roles.
- **Proficiency scale (declared):** 0 none · 1 aware · 2 working · 3 proficient · 4 expert. Each role
  skill has a required level r_k (1–4). The person's level c_k comes from the intake and is always a
  CLAIM (CV extraction with cited span, or self-rating); the app never calls it verified. Unknown
  skills (not mentioned, not rated) count as 0 and are shown as "not stated — tell us", separate from
  "missing".
- **Fit (0–100)** = 100 × Σ_k w_k · min(c_k / r_k, 1) / Σ_k w_k, with w_k = scenario emphasis weight
  (essentials included at their fixed weight).
- **Essential gate:** any essential skill or prerequisite below its required level is listed as an
  "essential gap"; the role is labelled "longer route" (still ranked, never hidden).
- **Outlook** (separate): role demand evidence + task evidence per scenario, with sources.
- **Learning effort** = verified-course hours to close the gap ÷ weekly hours (workload, not readiness).
- **Preference lens** (interests, SDG priorities): re-orders near-ties transparently; never changes fit.
- Gap: ready now (c_k ≥ r_k) / bridgeable (c_k = r_k − 1, or an adjacent skill exists) / missing.
- The person chooses a destination; new evidence only proposes revisions with a diff. No collaborative
  filtering (no interaction history).
- **What would change this recommendation?** Personal what-if: change hypothetical skill
  levels, weekly hours, budget or interests → same engine recomputes → exact score/gap/pathway deltas;
  the real profile is untouched until the user edits it. Evidence/assumption sensitivity: switch
  scenario, remove a source family or vary a declared assumption within its range → rank stability and
  the dependency causing a change. Smallest change to reach a chosen fit/gap condition is computed over
  verified resources (essentials preserved, protected attributes never changed); infeasible requests
  are explained. Results are model sensitivity, never claims about hiring success.

### 4.6 Pathway and SDG (must-haves 4, 5)
Prerequisite graph over a verified course catalogue (free MOOCs, Microsoft Learn, OpenLearn, Kaggle,
government/TVET; HRD Corp-claimable only when verified); weekly-hours budget; ordered week-by-week plan.
SDG mapping per role and skill: target + mechanism sentence + UN source; core 4.3/4.4/8.2/8.5, others
only where the work supports them (e.g. ESG reporting → 13.2). Test: nothing recommended without a
mapping. "Future-ready skills are sustainability skills" appears as ESG/green destination roles.
**Targeted vs robust first steps:** two plans under the same time/cost limits — one optimised
for the chosen role and scenario, one maximising the worst-case coverage across both scenarios
(max over plans of min over scenarios of coverage U(P,s); CP-SAT or enumeration over the small
catalogue) — with the full trade-off shown (hours, cost, coverage per scenario, essentials still
unmet). If both give the same plan, show one shared plan. Coverage of learning material is not
measured skill. When evidence changes, keep unaffected and user-recorded steps and propose the
smallest useful revision.

### 4.7 Fairness and privacy
PII stripped before matching; paired synthetic profiles differing only in protected fields must get
identical results (test; the badge names the test and date). HR sees aggregates only.

### 4.8 Hardest risks and fallbacks (named in the proposal)
| Risk | Control | Fallback |
|---|---|---|
| Thin / incomparable trend data | comparability checks, lineage count | "insufficient evidence", last good snapshot (stale label) |
| AI inventing jobs/courses/stats | closed catalogues, strict schemas, claim-to-passage check | item rejected, "no supported source" |
| Matching quality | labelled synthetic profiles test set | uncertainty shown, user edits skills |
| Provider failure (LLM, GPU) | time budgets | form instead of CV parse; BM25 search; text instead of voice |
| Source terms | per-source terms notes; MY job sites linked, not scraped | connector disabled with reason |
| Misuse of admin actions | admin token for pipeline run, review queue, source approval; profiles bound to a browser session | 403 with reason |

### 4.9 Visible on-screen agent (Burrow-inspired; not a tutor)
An agent icon always on screen. It acts on the real interface: a visible cursor moves to the real
element, and real external pages open in new tabs. Typed actions, validated by the app before they run:
open_evidence (drawer with the cited row/passage) · open_tab (real course page, real job-search
results, original source) · highlight (changed requirement, skill, step) · navigate (radar, role,
comparison, pathway) · compare_roles · explain (short spoken/written explanation of a score or a
change) · simulate (run a what-if, §4.5) · propose_pathway_update (user accepts or declines). Proactive moments: after intake ("here are
your top roles — I'll open the evidence for the first"), after a pipeline run that changed this user's
results ("new DOSM data changed your outlook — let me show you"), when the user asks "why?". Pause/stop
anytime; stop cancels queued actions and speech. Voice: browser speech (speak + listen, stop on
interrupt); text always available. It never tutors, hints or grades.
**Execution contract:** the server returns a plan of actions {action_id, type, target_id, params}. The
client validates each target exists and is allowed, moves the cursor, executes, and returns
{action_id, status: done | failed | blocked | cancelled, detail}; the agent continues from the actual
results (it knows whether a drawer opened, a navigation succeeded or a tab was blocked).
External tabs: browsers may block tabs not opened by a user click, so the agent opens tabs only from a
user gesture (the user clicks the agent's "open" card or says "open it"); if blocked, it shows the link
with a "click to open" button and reports "blocked". Opening a page gives NO control over that page;
the agent never claims to act inside it.
Look: a simple Qart icon (no character); voice off by default, one click to turn on.
Tabs and spoken interruption are tested in slice 1 (spike), not discovered later.

## 5. Stack
FastAPI (Python 3.12) · PostgreSQL on Replit (SQLite locally) · React + TypeScript + Vite + Tailwind ·
Recharts (radar, sparklines) · React Flow (pipeline canvas) · OpenAI gpt-4o-mini (extraction,
explanation, research agent, on-screen agent) · RunPod serverless BGE-M3 + reranker · Replit hosting +
Scheduled Deployment · browser Web Speech · Telegram Bot API (extra).

## 6. Data model
source · ingestion_run · observation · lineage · measure · task · task_change · skill · skill_weight ·
role · role_task · role_skill · crosswalk · status_label · forecast (+ backtest) · scenario · course ·
course_prerequisite · sdg_mapping · field_profile · research_question · research_finding ·
review_item · profile · profile_skill · match_run · destination_choice · pathway · change_record ·
agent_action · team · notification.

## 7. API
/intake/parse · /profiles · /radar · /match · /roles/{id} · /compare · /destination · /pathway ·
/changes · /why/{item} (evidence chain) · /pipeline/runs · /pipeline/run (locked) · /sources ·
/observations · /agent/research (findings, review queue) · /agent/act (on-screen agent: plan of typed
actions for the current screen) · /team (upload, heatmap) · /notify/telegram (extra).

## 8. Acceptance checks (before the demo)
1. Two different synthetic CVs → different radar focus, ranks, gaps and pathways, each justified.
2. A real fetch is stored with dates; a compatible older/newer comparison changes a traceable input and
   the ranking/pathway; "no change" shown honestly.
3. Scenario toggle changes requirements with an explanation; personal skills unchanged.
4. Every ranked role and recommended skill: source, SDG mapping with mechanism, real resources in
   prerequisite order with hours.
5. User's chosen destination persists; re-planning proposes a diff.
6. Research agent: a finding from a registered source publishes automatically and changes a traceable
   output; an eligible NEW source is admitted automatically; an ambiguous one is quarantined and
   promoted only after independent corroboration; an unsupported claim is rejected; a scope mismatch
   is not flagged as a contradiction.
7. On-screen agent: actions run on real elements/real pages; stop cancels queued actions and speech.
8. Fallback modes usable and labelled. 9. Backtest table reproducible from code.
11. What-if: one hypothetical edit gives the exact displayed delta and clearing it restores the
    original; removing irrelevant evidence changes nothing; targeted vs robust plans both respect
    budget and prerequisites (identical plans allowed).
10. **Central mechanism, reproducible end to end (scripted test + demo):** a published finding (with
    source and date) → a supported task-change interpretation (observed vs assumed labelled) → a
    scenario emphasis change → a different score/gap for profile A → a justified pathway revision
    proposal; the SAME finding gives profile B a different, explainable consequence (or none, and
    why). Observed facts and assumptions shown distinctly at every step.

## 9. Repository strategy
New branch `v3` from `main`. First commits: (a) rewrite the agent entry points that still describe the
old product — `AGENTS.md` (imported by `CLAUDE.md`) — and drop their references to `PROJECT_PLAN.md`
and `team/`, so no tool is steered back to the old idea; this plan becomes `docs/PLAN.md` in the repo;
(b) remove the old idea's code (training companion, cases, practice, evidence-from-practice engine,
optimiser, evaluation, old UI pages and their tests); keep only neutral infrastructure (Replit config
and start script, RunPod embedding worker, LICENSE, Python/Node config). Everything else written new.
README, declaration log and decision log rewritten. Merged into `main` slice by slice; the user pushes.

## 10. Build order (vertical slices, UI from slice 1; each slice ships its own validation,
persistence, access control, provider fallback and cancellation — no separate 'reliability later')
0. **Reset:** AGENTS.md/CLAUDE.md rewritten, docs/PLAN.md added, old code removed.
1. **Evidence:** DOSM + TalentCorp + Economic Index collectors, store, measures, task model for the
   field, backtest, run log + lock, source registry; first Radar + pipeline page with real data.
   Replit Scheduled Deployment set up here (manual step) so real run history accumulates.
2. **Journey:** intake (CV/form, extraction, skill mapping, PII) → matching → gaps → scenarios →
   pathway + SDG → destination; full UI; checks 1, 3, 4, 5.
3. **Research agent + change:** agent workflow (§4.2), replay of genuine historical releases + live
   refresh → recompute → What-changed view with the evidence chain; checks 2, 6.
4. **On-screen agent:** cursor, tabs, highlights, explanations, voice, proactive change walkthrough;
   check 7.
5. **Extras:** HR heatmap, EN/BM, mobile, Telegram, fairness test.
6. **Submission (drafting from slice 1):** PRD, deck, video script, README, declaration, Replit and
   RunPod proof, public Apache-2.0 repo, committee access.

## 11. Manual setup steps
Replit Scheduled Deployment + Secrets (slice 1) · Telegram bot via @BotFather (slice 5) · committee
GitHub access · demo video · team fields.

## 12. UI design (to approve as a clickable mockup before frontend code)
- **Character:** an evidence-first intelligence product — calm, data-dense, trustworthy (references:
  Linear and Stripe dashboards for workflows, IBM Carbon for tables, GitHub Primer for empty / loading
  / error states). Built with the frontend-design and web-design-guidelines skills.
- **System:** Tailwind + Radix primitives; Radix Colors scales with semantic roles (evidence = blue,
  assumption = amber, estimate = violet, stale/fallback = grey, SDG targets in official UN colours);
  Geist / Inter typography; WCAG AA contrast; keyboard navigable; light theme first.
- **Layout:** left journey stepper (Start → Radar → Matched → Pathway → Future you) · main canvas ·
  right evidence drawer (source, date, cited passage, observed/assumed tag) · agent dock bottom-right
  (icon, status, plan of actions, stop) · top bar with scenario toggle, language EN/BM, data freshness.
- **Signature visuals:** Future Skills Radar (radar chart + rising/weakening lists with sparklines);
  Get matched cards with a stacked fit bar and the 3-column gap; Today → Future you split view; the
  animated live-intelligence pipeline canvas; What changed diff view; agent cursor gliding to targets.
- **States:** every data element has loading, empty, stale, fallback and error states that name the
  reason. Mobile: stepper becomes top tabs, drawer becomes a bottom sheet, agent dock stays.
- **Process:** slice 0 produces a clickable mockup (static HTML) of Start, Radar, Get matched, Pathway,
  Today → Future you and the pipeline page for approval; slices then build the real UI to it.

## 13. Optional (not in current scope)
Agent-found YouTube learning videos; more on-screen agent capabilities.
