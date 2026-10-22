# Qart.ai: wiring the six-screen flow to the backend

*Brief for Claude Code. Written 22 Oct 2026 by Meiirman (Person B). Screens are in `design/qart-flow/screens/`.*

## 0. Read first

1. `AGENTS.md` (hard rules), `team/00_SHARED_CONTRACT.md` (API contract v2), `PROJECT_PLAN.md`.
2. `src/contract.py` (Pydantic models), `src/api_engine.py`, `src/api_search.py`.
3. `.claude/skills/qart-design-system/SKILL.md` and `web/src/ui.tsx` for UI.
4. The six screens in `design/qart-flow/screens/` (see §2 for how to read them).

## 1. What this task is (and is not)

**The backend already exists.** Most of what the six screens need is already served by FastAPI (`src/main.py`). Do **not** build a new backend, a second API, or a new database.

The task is:
1. Map each screen to the existing endpoints (§3).
2. Build or extend the React pages in `web/` so the flow works end to end against the real API.
3. Identify the few real gaps (§5), write them up, and **stop for approval** before changing any backend code.

**Ownership (contract §1).** I am Person B: I own `web/`, `src/companion/`, `src/api_companion.py`, `cases/`. Person A owns `src/engine/`, `src/api_engine.py`, `src/store.py`, `catalogue/`, `data/`, `eval/`. `src/main.py` and `schemas/` are shared. **Do not edit Person A's folders, `schemas/` or `src/contract.py` without my explicit go-ahead in chat.** Any contract change also needs Person A's agreement and a version bump.

## 2. How to read the screen files

The `.dc.html` files are design-canvas components, not runnable pages: they need a canvas runtime (`support.js`) that is not in this repo. Read them as **layout + content specs**:
- the markup inside `<x-dc>` is the layout and copy;
- `{{name}}` holes are filled by `renderVals()` in the `<script type="text/x-dc">` block at the bottom;
- `<sc-for>` is a loop, `<sc-if>` is a conditional; `<a href="X.dc.html">` is navigation between screens.

**Use them for structure, wording and flow only.** Visual styling must follow the repo's qart-design-system skill (tokens, `ui.tsx` components, Lucide icons, GSAP motion), not the mockup's hex colours.

**Every number in the mockups is illustrative and must not be copied into code or seed data.** This includes posting counts, "+52%" skill trends, scores out of 100, "±5" bands, "30–45% of tasks", demand ranges, course names, hours and the "[Training provider]" placeholder. Real values come from the API (AGENTS.md: never invent jobs, courses or statistics; every number is labelled evidence, assumption or synthetic).

## 3. Screen → endpoint map

| # | Screen file | Feature (hackathon table) | Existing endpoints / data | Existing page to extend |
|---|---|---|---|---|
| 1 | `Main.dc.html` | Skills profile intake | `POST /api/profile`, `GET /api/profile/{user_id}` | `web/src/pages/Intake.tsx` (`/start`) |
| 2 | `Signals.dc.html` | AI-trend signal layer | `GET /api/snapshots`, `GET /api/snapshots/diff?from=&to=`, `POST /api/ingest/run` | new page (or a section of `Evidence.tsx` re-scoped for employees) |
| 3 | `Matches.dc.html` | Future-role matching | `GET /api/recommendations/{user_id}?scenario=assistive\|agentic` | `MyFuture.tsx` (`/future`) |
| 4 | `Pathway.dc.html` | Personalised reskilling pathway | `GET /api/path/{user_id}?role_id=&weekly_hours=`, `GET /api/resources/{skill_id}`, `GET /api/search` | `MyFuture.tsx` path section / `ResourceList.tsx` |
| 5 | `Impact.dc.html` | SDG mapping | `sdg_targets` on `RoleRecommendation` and `PathStep`; `catalogue/sdg_map.json` | new page or a section of `MyFuture.tsx` |
| 6 | `Scenarios.dc.html` | Handling uncertainty | `GET /api/recommendations` called for **both** scenarios; `RoleOutlook` (`ai_handled_share`, `oversight_share`, `label`, `because`, `basis`); `changed_since` | `MyFuture.tsx` scenario switch, or a new page |

Mockup → contract translations that must be applied:

| Mockup shows | Use instead |
|---|---|
| "Moderate / Fast AI disruption" | Contract enum `assistive` / `agentic` (UI labels may say "AI helps with routine work" / "AI does most routine work") |
| Match score "84/100 ± 5" | `score` (0–1 suitability indicator, **not a probability**) or `fit`, with `factors` and `formula` shown verbatim; keep `score_note` |
| Score parts 40/20/25/15 | The real formula: `0.55*coverage + 0.20*confidence + 0.10*interest − 0.15*effort` (effort is a penalty) |
| "Have / to learn" chips | `gap[]` with each skill's evidence `state` (`StatePill`), never a percentage |
| "30–45% of your tasks could be automated" | `outlook.ai_handled_share` per scenario, labelled **assumption (company layer B)**, with `basis` and `because` |
| Skill demand bars and dates | Snapshot `signals[]` and `/snapshots/diff`, each with `source`, `release_date`, `retrieved_at`, `url` |
| "Refresh" button per source | `POST /api/ingest/run` (labelled "historical data replay" in the demo, per contract §6 step 6) |
| Six SDG goals (4, 8, 9, 12, 13, 16) | Only the targets in `catalogue/sdg_map.json` (currently 4.4, 8.2, 8.5) with their rationales and UN links. Don't add goals the catalogue doesn't declare |
| Pathway courses, hours, "HRD Corp claimable" | `PathStep` fields: `title`, `hours`, `cost`, `url`, `retrieved`, `because`. Courses come only from `catalogue/courses.json`; `hrd_claimable` is currently `false` for all, so **don't show an HRD Corp badge** unless a verified listing is added to the catalogue |
| Weeks at N h/week | Re-request `/api/path` with `weekly_hours`; `total_hours` and `weeks` come from the planner |
| "Siti" | The current persona / profile `display_name` (`useUserId`, `PersonaProvider`) |

## 4. Intake form (screen 1): keep what the engine needs

The new form must **keep the existing self-rating section from `Intake.tsx`** (`skills_self_reported` confidences). The recommender's `confidence` factor uses them, and golden journey step 1 depends on them ("Aina self-rated 8/10 on adjustments"). Place it as its own card on the form, styled like the other cards.

Fields that map onto the current `Profile`:
- current role → `current_role_id` (a select from `GET /api/roles`, not free text)
- years of experience → `years_experience` (map the chip to a number, e.g. the band's midpoint)
- "What do you enjoy?" → `interests`
- weekly learning hours → `weekly_learning_hours`
- `display_name`, `team`, `language` as `Intake.tsx` does today.

## 5. Real gaps: propose, don't implement yet

Write these up in `docs/screens_gap_report.md`, then stop and wait for me.

1. **New intake fields** that `Profile` doesn't have: industry, highest education, tools used, direction (grow / adjacent / switch), timeframe, preferred learning formats, comfort with AI tools, free-text notes.
   - Proposal: one optional `preferences` object on `Profile` (additive, default empty), so existing clients and tests keep working.
   - State which ones the engine would actually use (e.g. timeframe → planner horizon, formats → course ranking). Unused ones are stored but **not shown as affecting the score** until Person A wires them in.
   - Free text: synthetic demo data only; don't send it to any LLM or log it.
2. **SDG read endpoint (optional).** If the UI needs target titles and rationales and they aren't already in an API response, propose a read-only `GET /api/sdg` that returns `catalogue/sdg_map.json`. It's shared `main.py` plus Person A's catalogue, so it needs approval.
3. **Skill-demand view for employees.** If `/snapshots` signals aren't enough for the "skill demand" chart, list exactly what's missing. Do not fabricate a trend series.
4. **Known engine bug (Person A, from `Qart.ai_design_merge_notes.md` §1).** `HELP_PHRASE` in `src/engine/skills.py` has no key `0`, so a walk-back correction without help returns 500. Note it in the report; don't fix it unless I say so.

## 6. Order of work

1. Read §0 files. Post a short plan: which pages change, which are new, and where they go in the nav (`App.tsx`, employee role).
2. Write `docs/screens_gap_report.md` (§5). **Stop for approval.**
3. Frontend, one screen per commit, in order 1 → 6, against the real API (`VITE_USE_MOCKS=false`). Add mocks in `web/src/api.ts` only where an endpoint is pending approval, clearly marked.
4. Backend additions, only those I approve, each with tests and a contract-version note for Person A.
5. Log any new library in `docs/DECLARATION_LOG.md`.

## 7. Done when

- `python -m pytest` passes (227+), `cd web && npx tsc -b && npm run build` is clean, `npm run lint` adds no new warnings.
- Golden journey steps 1–5 (contract §6) still pass for persona Aina, and step 6 (newer snapshot → assumption review → recompute) is visible from the Signals and Scenarios screens.
- Every number on the six screens shows a source + date or an assumption/synthetic label; no mastery percentages anywhere.
- Desktop (1440px) and phone (375px) have no sideways scroll.
- Commits are small, on branch `b/app`, with meaningful messages.
