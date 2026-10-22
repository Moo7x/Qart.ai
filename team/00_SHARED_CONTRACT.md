# Qart.ai · 00: Shared contract (both people read this first)

*Agree on this file together in the Day-0 session (about 1.5 h). It is the only thing both sides must share before working separately. If either of you needs to change it later: **stop, message the other, bump the version, update both sides.***

Contract version: **v2** (21 Oct 2026). v2 aligns with `PROJECT_PLAN.md` v2:
- Events carry difficulty and companion-error/ambiguity flags.
- Skill states follow explicit rules, with no percentages shown in the UI.
- Snapshots hold external evidence only; company adoption assumptions are a separate editable object.
- The recommender uses the v2 additive formula and returns a requirement card.
- HR endpoints are aggregate-only.
- The optimiser can only edit the playbook and is judged on a separate acceptance set.

**v2.1 additions (22 Oct 2026, additive; old clients unaffected), for the six-screen flow (`design/qart-flow/`):**
- `Profile.preferences` (optional, default empty): industry, education, tools, direction (`grow`/`adjacent`/`switch`), timeframe_months (3/6/12), formats, ai_comfort (0–10), notes (≤500 chars, synthetic, never logged or sent to an LLM). **Stored only: no engine factor reads them yet**, so rankings and the golden-journey numbers are unchanged (pinned by a test).
- `GET /api/sdg`: read-only SDG map from `catalogue/sdg_map.json` (targets with titles, UN links, rationales; role and skill tags; `about` = "declared judgment, not external evidence").
- Fix: a walk-back corrected without help (`missed_then_found`, help 0) is now explained ("on a second look, without help") instead of returning 500. Evidence rules unchanged.

---

## 1. Repo layout (who owns what)
Start from the organisers' template repo (`codex/drive_info/.../SDC Hackathon Submission Template (GitHub)`). Keep its files: `LICENSE` (Apache-2.0), `README.md`, `.replit`, `requirements.txt`, `.env.example`, `runpod/handler.py`, `submission/`, `tests/`.

```
.
├── AGENTS.md                 # shared rules for coding agents (both) – see §7
├── CLAUDE.md                 # one line: @AGENTS.md  (+ personal notes are NOT committed)
├── schemas/                  # BOTH – this contract as JSON examples (+ optional JSON Schema)
├── src/
│   ├── main.py               # BOTH – FastAPI app; includes both routers; serves web/dist
│   ├── engine/               # A – skill model, recommender, scenarios, planner, SDG, snapshots
│   ├── api_engine.py         # A – engine routes
│   ├── companion/            # B – agent, tools, playbooks/, grader
│   ├── api_companion.py      # B – companion + cases routes
│   └── store.py              # A – tiny persistence (SQLite file or Replit Postgres)
├── catalogue/                # A – roles.json, courses.json, sdg_map.json, skills.json
├── data/                     # A – raw/ (gitignored if large), processed/, snapshots/
├── cases/                    # B – case_*.json (+ ground truth)
├── web/                      # B – React + TypeScript (Vite)
├── eval/                     # A – evaluation runner + results
├── runpod/handler.py         # A – GPU endpoint (embeddings/reranker)
├── docs/                     # BOTH – decision_log.md, DECLARATION_LOG.md, architecture.md, screenshots
├── submission/               # BOTH – PRD, declaration, proofs (PDFs)
└── tests/                    # each tests their own folder
```
**Rule:** never edit the other person's folders without asking. `src/main.py` and `schemas/` are shared, so change them only with a message.

## 2. Git workflow (genuine history matters to the judges)
- `main` is protected by habit: only merge at checkpoints.
- Branches: `a/engine` (Person A) and `b/app` (Person B). **Push at least 3–4 times a day** with meaningful messages (`engine: add help-weighted BKT update`). Never one giant commit.
- The repo is **private** until 24 Oct, then **public**. Add the committee GitHub accounts as collaborators (handles from Discord/Drive).
- **No keys in the repo.** Use Replit Secrets and a local `.env` (gitignored). Update `.env.example` with variable *names* only.
- **After the deadline (25 Oct 07:59) the repo is frozen.** No pushes unless the organisers allow (e.g. the Upgrade Round).

## 3. Shared vocabulary

### Skill IDs (practised in cases)
| skill_id | Meaning |
|---|---|
| `recon_to_source` | Reconcile a balance back to source evidence |
| `duplicate_detection` | Spot duplicate or double-counted entries |
| `cutoff_timing` | Judge period cut-off and timing items (deposits in transit, uncleared cheques) |
| `unsupported_adjustment` | Challenge manual adjustments without support |
| `fx_conversion` | Verify currency conversion and the rate used |
| `transposition_check` | Catch keying/transposition errors (1,520 vs 1,250) |
| `escalation_judgment` | Decide to sign off, correct, or escalate |
| `ai_output_review` | Ask for the evidence that would change the AI's conclusion |

### Skill IDs (future-role skills, from catalogue/courses only)
`variance_analysis`, `data_quality`, `controls_design`, `process_automation`, `stakeholder_communication`, `forecasting`, `spreadsheet_modelling`, `sql_basics`. (Person A may add more; announce it.)

### Enums
- **help_level**: `0` none · `1` question · `2` hint · `3` explanation · `4` answer shown
- **case mode**: `practice` (has ground truth) · `checkin` (no help allowed, has ground truth) · `real` (synthetic "real work", ground truth hidden from the user)
- **decision**: `sign_off` · `correct` · `escalate`
- **skill state**: `self_reported` · `observed_with_help` · `demonstrated_independently` · `insufficient_evidence`
- **scenario**: `assistive` (AI helps with routine work) · `agentic` (AI does most routine work; humans review and decide)
- **cause_if_wrong**: `worker_gap` · `ai_error` · `data_issue` · `ambiguous` · `null`

## 4. Objects (JSON examples; put each in `schemas/examples/`)

**Profile**
```json
{"id":"u_aina","display_name":"Aina (synthetic)","current_role_id":"recon_associate","years_experience":0.5,
 "skills_self_reported":[{"skill_id":"recon_to_source","confidence":0.85},{"skill_id":"unsupported_adjustment","confidence":0.8}],
 "interests":["analysis","automation"],"weekly_learning_hours":4,"language":"en","team":"finops_kl"}
```

**Case** (`GET /api/cases/{id}` returns everything **except** `ground_truth`)
```json
{"id":"case_003","title":"Oct bank reconciliation – Kopi Kita Sdn Bhd","mode":"practice","difficulty":2,
 "scenario_variant":"assistive",
 "ledger":[{"row_id":"L4","date":"2026-10-14","description":"Supplier payment – Beans Co","amount":-1520.00,"currency":"MYR","doc_ref":"INV-1043"}],
 "bank":[{"row_id":"B6","date":"2026-10-15","description":"TRF BEANS CO","amount":-1250.00,"currency":"MYR"}],
 "documents":[{"doc_ref":"INV-1043","type":"invoice","text":"Beans Co Sdn Bhd … Total RM1,250.00"}],
 "ai_output":{"claim":"Account reconciles. Difference RM0.00 after adjustment ADJ-7.",
   "proposed_adjustments":[{"id":"ADJ-7","amount":270.00,"reason":"rounding difference"}]},
 "ground_truth":{"has_issue":true,"issue_types":["transposition_check","unsupported_adjustment"],
   "affected_rows":["L4","ADJ-7"],"correct_decision":"correct",
   "explanation":"Ledger keyed 1,520 instead of 1,250; ADJ-7 hides it as 'rounding'.",
   "skills":["transposition_check","unsupported_adjustment","ai_output_review"]}}
```

**Event** (produced by B at decision time → `POST /api/events`)
```json
{"id":"ev_0001","user_id":"u_aina","case_id":"case_003","mode":"practice","scenario":"assistive",
 "timestamp":"2026-10-22T10:15:00+08:00","self_confidence_before":0.8,
 "help_level_max":2,"help_steps":["question","hint"],"checks_used":["recompute_totals","match_entries"],
 "user_decision":"correct","decision_correct":true,"issue_found_by":"user",
 "skills_evidence":[{"skill_id":"transposition_check","outcome":"success","help_level":2},
                    {"skill_id":"unsupported_adjustment","outcome":"success","help_level":1}],
 "cause_if_wrong":null,"companion_version":"playbook_v1","duration_sec":420,
 "difficulty":2,"session_id":"s_0004",
 "flags":{"companion_error":false,"ambiguous_case":false,"data_issue":false}}
```
Events flagged `companion_error` or `ambiguous_case` are stored but **don't count** toward or against a skill. The employee, a senior, or the grader can set the flag.

**SkillState** (A returns; the UI shows `state`, `why` and `evidence_trail`, **never a percentage**)
```json
{"user_id":"u_aina","skill_id":"unsupported_adjustment","state":"observed_with_help",
 "why":"1 of 2 independent successes (checkin_001). Needs 1 more on a different case in a separate session. case_006 was solved after a question (help 1), so it counts as help-assisted.",
 "next_to_confirm":"checkin_002 (later session)",
 "evidence_trail":[{"event_id":"ev_0001","case_id":"case_003","outcome":"missed_then_found","help_level":2},
                   {"event_id":"ev_0002","case_id":"case_006","outcome":"success","help_level":1},
                   {"event_id":"ev_0003","case_id":"checkin_001","outcome":"success","help_level":0}],
 "counted_events":3,"independent_successes":1,"self_confidence":0.8,
 "provisional_estimate":0.58,"estimate_note":"internal, used only to order practice; parameters are provisional assumptions",
 "last_updated":"2026-10-22T10:40:00+08:00"}
```
**State rules (v2):**
- `insufficient_evidence` = fewer than 2 counted events.
- `observed_with_help` = at least one success with help ≥1, or mixed results.
- `demonstrated_independently` = ≥2 independent successes (help 0, at least one a check-in) on different cases, in separate sessions, with no independent failure since.
- `self_reported` = intake claim only.

**Role** (`catalogue/roles.json`)
```json
{"id":"ai_finops_analyst","title":"AI Finance Operations Analyst","internal":true,
 "based_on":[{"source":"O*NET 31.0","code":"13-2051.00","title":"Financial and Investment Analysts","url":"https://www.onetonline.org/link/summary/13-2051.00"}],
 "skills":[{"skill_id":"ai_output_review","base_weight":0.9},{"skill_id":"variance_analysis","base_weight":0.7}],
 "sdg_targets":["4.4","8.2"],"summary":"Reviews AI-prepared reconciliations and reports; owns exceptions."}
```

**Snapshot** (A): **external evidence only (layer A)**. Usage ≠ replacement.
```json
{"id":"snap_aei_2026_05","source":"Anthropic Economic Index (data CC-BY)","release_date":"2026-06-26","period":"2026-05",
 "geo":"MYS+GLOBAL","url":"https://huggingface.co/datasets/Anthropic/EconomicIndex","retrieved_at":"2026-10-21",
 "signals":[{"entity":"SOC 43-3031 Bookkeeping, Accounting & Auditing Clerks","metric":"usage_pct","geo":"GLOBAL","value":0.32},
            {"entity":"MYS overall","metric":"automation_pct","value":47.2}],
 "suggested_assumption_reviews":[{"assumption_id":"agentic.matching","reason":"usage on bookkeeping tasks rose 0.30→0.32 (Apr→May 2026)"}]}
```

**CompanyAssumptions** (A stores; HR edits; **layer B**: explicit, labelled assumptions, synthetic in the prototype)
```json
{"version":3,"updated_by":"HR (synthetic)","based_on_snapshot":"snap_aei_2026_05",
 "scenarios":{"assistive":{"tasks":{"match_transactions":"ai_drafts_human_reviews","prepare_adjustments":"human","sign_off":"human"}},
              "agentic":{"tasks":{"match_transactions":"ai","prepare_adjustments":"ai_drafts_human_reviews","sign_off":"human"}}},
 "shift_rule":"when a task moves to ai_drafts_human_reviews or ai, 50% (assistive) / 80% (agentic) of its execution-skill weight moves to oversight skills"}
```

**Recommendation** (A: `GET /api/recommendations/{user}?scenario=agentic`)
```json
{"user_id":"u_aina","scenario":"agentic","snapshot_id":"snap_aei_2026_06",
 "assumptions_version":3,
 "roles":[{"role_id":"ai_finops_analyst","rank":1,"score":0.52,
   "factors":{"coverage":0.60,"confidence":0.50,"interest":0.60,"effort":0.40},
   "formula":"0.55*coverage + 0.20*confidence + 0.10*interest - 0.15*effort",
   "gap":[{"skill_id":"variance_analysis","state":"insufficient_evidence","weight":0.20}],
   "requirement_card":{"tasks":[{"task":"Review AI-prepared reconciliations","onet":"13-2051.00","allocation":"ai_drafts_human_reviews"}],
     "weights":[{"skill_id":"ai_output_review","base":0.15,"scenario":0.27,"because":"agentic: matching moves to AI → 80% of its execution weight shifts to oversight (assumption v3)"}],
     "evidence":[{"label":"AEI May 2026, SOC 43-3031 usage 0.32","url":"…"}]},
   "sources":[{"label":"O*NET 13-2051.00","url":"…"},{"label":"AEI release 2026-06-26 (CC-BY)","url":"…"}]}],
 "changed_since":{"assumptions_version":2,"rank_changes":[{"role_id":"ai_finops_analyst","from":3,"to":1,"because":"…"}]}}
```
The score is a **suitability indicator, not a probability**. `effort` is a **penalty** (subtracted).

**PathPlan** (A: `GET /api/path/{user}?role_id=&weekly_hours=`)
```json
{"user_id":"u_aina","target_role_id":"ai_finops_analyst","weekly_hours":4,"robust_across":["assistive","agentic"],
 "steps":[{"order":1,"type":"practice_case","ref":"case_007","title":"Unsupported adjustments – 3 cases","hours":1.5,"skills":["unsupported_adjustment"],"cost":"free"},
          {"order":2,"type":"course","ref":"course_12","title":"…","hours":3,"skills":["variance_analysis"],"url":"…","cost":"free","retrieved":"2026-10-21","sdg_targets":["4.4"]}],
 "total_hours":18,"weeks":5,"worst_case_gap":0.22}
```

**Course** (`catalogue/courses.json`)
```json
{"id":"course_12","title":"…","provider":"…","url":"…","hours":3,"cost":"free","skills":["variance_analysis"],"prerequisites":[],"retrieved":"2026-10-21"}
```

**OptimizerProposal** (A creates; B shows in the Senior console)
```json
{"id":"opt_001","editable_scope":"playbook","base_version":"playbook_v1","candidate_version":"playbook_v2",
 "diff":"+ Always compare each manual adjustment to a document before accepting it.",
 "optimisation_set":{"before":"9/14","after":"12/14"},
 "acceptance_set":{"before":"14/20","after":"17/20","criteria_hash":"sha256:…","false_alarms_clean":{"before":"1/6","after":"1/6"},"invalid_citations":0},
 "regressions":[],"status":"pending","decided_by":null,"decided_at":null,"rollback_to":"playbook_v1"}
```
Results are **counts on synthetic variants**. The acceptance set and its criteria live outside the optimiser's reach (separate folder, hashed).
**Playbook:** `src/companion/playbooks/playbook_vN.md` is the companion's editable checking procedure. **B owns the format; A's optimiser writes candidates to `playbooks/candidates/`.** Only an approved candidate becomes active.

## 5. API endpoints
| Method + path | Owner | Returns |
|---|---|---|
| `POST /api/profile` | A | Profile + initial SkillStates |
| `GET /api/skills/{user_id}` | A | SkillState[] |
| `POST /api/events` | A | updated SkillState[] |
| `GET /api/snapshots` · `GET /api/snapshots/diff?from=&to=` | A | Snapshot[] / diff |
| `GET /api/roles` | A | Role[] |
| `GET /api/sdg` *(v2.1)* | A | SDG targets (title, UN link, rationale) + role/skill tags from the catalogue |
| `GET /api/recommendations/{user_id}?scenario=&snapshot=` | A | Recommendation |
| `GET /api/path/{user_id}?role_id=&weekly_hours=` | A | PathPlan |
| `GET /api/next-case/{user_id}?scenario=` | A | `{"case_id": "...", "because": "..."}` |
| `GET /api/hr/summary?team=&scenario=` | A | Aggregates only: per skill, counts of people in each state (groups <5 suppressed), training demand per scenario. **No names, no "who should move where"** |
| `GET /api/assumptions` · `PUT /api/assumptions` | A | CompanyAssumptions (layer B); PUT bumps the version (HR, synthetic) |
| `POST /api/events/{id}/flag` | A | Mark an event `companion_error` / `ambiguous_case` (employee or senior) |
| `GET /api/optimizer/proposals` · `POST /api/optimizer/proposals/{id}/decision` | A | OptimizerProposal |
| `GET /api/cases?user_id=` · `GET /api/cases/{id}` | B | Case (no ground_truth) |
| `POST /api/companion/{session_id}/message` | B | `{"reply": "...", "help_level": 1, "ui_actions": [{"type":"highlight_rows","rows":["L4","B6"]},{"type":"open_document","doc_ref":"INV-1043"},{"type":"show_check","check":"recompute_totals","result":"RM270 unexplained"}], "trace": ["checking totals","matching rows"]}` |
| `POST /api/companion/{session_id}/decision` | B | Event (B then calls A's `POST /api/events`) |

All under one FastAPI app (`src/main.py`); web is built to `web/dist` and served by FastAPI.

**Python functions (not HTTP) that cross the boundary:**
- B provides `src/companion/auto.py → auto_diagnose(case: dict, playbook_path: str) -> {"has_issue": bool, "issue_types": [...], "affected_rows": [...], "decision": "...", "explanation": "...", "tool_calls": [...]}`. The companion diagnoses the case on its own, with no user and **without seeing ground_truth**. A's evaluation runner and optimiser call it.
- B provides `src/companion/grader.py → grade(case: dict, decision: str, flagged_rows: list) -> {"decision_correct": bool, "skills_evidence": [...]}`. Only the grader reads `ground_truth`.

## 6. Checkpoints (both)
| When | What | Stop rule |
|---|---|---|
| **M0** Wed 21 Oct, together, ~1.5 h | Agree on this contract, repo + branches, Replit project, LLM key in Secrets | Don't start building before this |
| **C1** Thu 22 Oct ~14:00, 30-min call | Each side shows its JSON matching the contract (A: real endpoint outputs; B: events from the companion) | Contract changes are agreed here |
| **M1** Thu 22 Oct ~21:00, together, 2–3 h | Merge to `main`; swap B's mocks for A's endpoints; run the **golden journey test** (below) | Stop new features until it passes |
| **C2** Fri 23 Oct ~14:00, 30-min call | Phase-2 progress, decide what to drop | Anything not working by 18:00 goes behind a flag |
| **M2** Fri 23 Oct ~22:00, together | Full demo rehearsal with the video script | Feature freeze after this |
| **M3** Sat 24 Oct ~15:00 | Video recorded, docs done, repo public | Submit by ~22:00, not at 07:00 |

**Build in increments (PROJECT_PLAN §9):** every increment ends **deployed on Replit and committed**. Spikes are timeboxed and droppable.
- **Increment 0, Base** (Thu midday): one case end to end; all six must-haves at a minimal level.
- **Increment 1** (M1): golden journey steps 1–5.
- **Increment 2** (Fri midday): step 6.
- **Increment 3** (Fri afternoon): step 7 + evaluation numbers.
- **Spikes:** RunPod (3 h), voice (2 h), improvement gate (4 h).
- Polish last.

**Golden journey test (M1 must pass steps 1–5; M2 adds steps 6–7), on the Replit URL:**
1. Aina's profile loads (self-rated 8/10 on adjustments).
2. case_003: Aina signs off → the grader shows the miss → stepped help → she finds it at hint level → event recorded (missed, then found with hint).
3. Next case is targeted at `unsupported_adjustment` (case_006) → caught after one question (help 1).
4. Check-in (no help) → caught → state stays `observed_with_help` with **"1 of 2 independent successes"**, the evidence trail and "why". *(Optional: a second check-in in a new, labelled session → `demonstrated_independently`.)*
5. Path visibly revised: the adjustments learning module is replaced by **one confirmation check-in**, the next gap moves up, and the ranking updates, each change traced to her events.
6. **Updated external evidence:** ingest the newer dated snapshot through the pipeline → signal diff → suggested assumption review → HR (synthetic) approves → requirement card shows the allocation and weight change → recommendations recompute (labelled "historical data replay"). The scenario toggle is shown as well, but doesn't replace this.
7. One clean case signed off correctly, and the AI false-alarm case handled (no "flag everything").

## 7. `AGENTS.md` (commit at the repo root; both coding agents read it)
```markdown
# Project rules for coding agents
Project: Qart.ai – SDC Hackathon 2026, Domain 1. A web app where employees review
AI-prepared finance work with a step-by-step companion; events become skill evidence; dated public trend
data drives explainable future-role matching and a learning path. Read PROJECT_PLAN.md and team/00_SHARED_CONTRACT.md.

Hard rules (hackathon):
- Synthetic or public/open data only. Never add real personal data or real CVs.
- Never invent jobs, courses or statistics. Every recommendation/claim shown to users carries a source + date.
- Humans decide. The system recommends; it never makes hiring/promotion/dismissal decisions.
- Never show users a mastery percentage. Show evidence states, the cases behind them, and why they changed.
- Label every number as evidence (dated source), assumption (company layer B / declared parameter) or synthetic.
- HR sees aggregates only (groups under 5 suppressed, which reduces but doesn't eliminate re-identification risk). Individual recommendations are employee-facing only.
- Acceptance cases (eval/acceptance/) are never read by the optimiser and never used to tune anything. Run each candidate against them once.
- The optimiser may only edit src/companion/playbooks/. It must never read the acceptance set or change grading criteria.
- No secrets in code or commits. Read keys from environment variables only.
- Respect the JSON contract in schemas/. If a change is needed, stop and tell the human.
- Only edit the folders owned by the person you are working for (see team/00_SHARED_CONTRACT.md §1).

Engineering rules:
- Small, reviewable changes; one feature per commit; meaningful commit messages.
- Prefer simple, explainable logic. Comment the "why" of every formula/weight.
- Add/maintain tests for your module (python -m unittest / pytest; vitest for web if used).
- Log every new library, model, dataset or API with its licence in docs/DECLARATION_LOG.md.
- The human must understand every component: explain non-obvious code in the PR/commit message.
```
`CLAUDE.md` (for Claude Code users) contains just: `@AGENTS.md`. Codex reads `AGENTS.md` directly.
