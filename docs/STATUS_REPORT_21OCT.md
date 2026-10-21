# Qart.ai — Status Report (21 Oct 2026)

---

## Person B (`b/app`) — DONE

### Backend — companion & API

- **`src/companion/agent.py`** — full stepped-help companion: help ladder (0–4), `missed_then_found` two-step flow, per-case session state (resets messages + help level on case change), checkin mode (no held-back events, always `help_level=0`)
- **`src/companion/grader.py`** — grades decisions against ground_truth, returns `success` / `failure` per skill
- **`src/companion/auto.py`** — headless diagnosis runner for Person A's evaluation (rule-based + optional LLM path)
- **`src/companion/tools.py`** — `recompute_totals`, `match_entries`, `list_adjustments`, `find_document`
- **`src/api_companion.py`** — REST routes:
  - `GET /api/cases`
  - `GET /api/cases/{id}`
  - `POST /api/companion/{session}/message`
  - `POST /api/companion/{session}/decision`
  - `POST /api/companion/{session}/flag`
- Event posting: tries direct store import first, falls back to HTTP, logs but never crashes if engine is absent

### Cases

- **`cases/`**: `case_001` (clean), `case_002` (duplicate), `case_003` (transposition), `case_004` (cutoff), `case_005` (FX), `case_006` (unsupported adjustment), `case_007` (AI false alarm), `checkin_001`, `checkin_002`
- **`eval/acceptance/`**: 17 graded cases (a001–a012 errors, c001–c005 clean) — all arithmetic verified
- **`eval/holdout/`**: 3 held-out cases (h001–h003) — untouched until final scoring

### Frontend — React / TypeScript

| Screen | Status |
|---|---|
| `Intake.tsx` | Self-rating sliders, interests, weekly hours; pre-fills from existing profile on load |
| `Workspace.tsx` | Ledger table, bank table, documents panel, AI claim + adjustments, companion chat, decision buttons |
| `MySkills.tsx` | Skill states (self_reported → demonstrated_independently), why sentence, evidence trail, no percentages |
| `MyFuture.tsx` | Role cards with `fit`, `time_to_ready`, `close_match`, `outlook`, `score_note`; dynamic snapshot banner from API |
| `HRSummary.tsx` | Aggregate skill counts by team, groups <5 suppressed, loads from API |
| `Result.tsx` | Correct/incorrect feedback, missed rows, null-safe event handling |

### Quality gates

- 33 tests passing (`pytest`)
- 0 ruff errors (Python 3.10 target)
- 0 mypy errors
- `npm run build` passes

### Still to do (Person B)

- **Issue 10 — UI design pass**: card shadows, alternating table rows, amber highlight for flagged rows, bigger decision buttons, skill badge colours, outcome badges on evidence trail
- Cases `case_004`, `case_005`, `case_008`, `real_001`, `real_002` not yet written (optional based on time)

---

## Person A (`a/engine`) — what is needed

### Must have before M1 merge (Thu 21 Oct 21:00 MYT)

| What | Endpoint | Why |
|---|---|---|
| Store events | `POST /api/events` — receives `CompanionEvent` JSON, stores to SQLite | `_post_event_to_engine()` already calls it; currently falls back to HTTP no-op |
| Skill states | `GET /api/skills/{user_id}` — returns `SkillState[]` | `MySkills.tsx` currently shows mock data |
| Snapshots | `GET /api/snapshots` — returns `Snapshot[]` | `MyFuture.tsx` calls it; currently using mock |
| Recommendations | `GET /api/recommendations/{user_id}` — returns `RoleRecommendation[]` | `MyFuture.tsx` mock until M1 |
| HR summary | `GET /api/hr/summary?team=finops_kl` — returns `HRSummaryData` | `HRSummary.tsx` mock until M1 |

### Evaluation (already handed over on `b/app`)

- `eval/acceptance/` — 17 graded cases; A's runner should read these
- `eval/holdout/` — 3 held-out cases; **do not look at these until final scoring**
- `src/companion/auto.py` — headless runner A can call from their eval script

### Contract reminders for A

- `CompanionEvent` matches contract v2 exactly: includes `difficulty`, `flags.companion_error`, `flags.ambiguous_case`
- **`DecisionResponse.event` can now be `null`** — for wrong practice decisions (held back until correct); A's store must handle `null` gracefully and not crash
- `SkillState` must include `state`, `why`, `next_to_confirm`, `evidence_trail` — `MySkills.tsx` renders all four fields
- HR summary: any group with count < 5 must return `null` for that count — the UI already renders `null` as "suppressed"

### Merge checklist (M1)

1. Merge `a/engine` + `b/app` → `main`
2. Set `USE_MOCKS = false` in `web/src/api.ts`
3. Smoke test: complete `case_003` as Aina → verify event appears in `GET /api/skills/u_aina` evidence trail
