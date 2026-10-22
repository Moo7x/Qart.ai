# Six-screen flow: gap report

*22 Oct 2026 · Person B · for `design/qart-flow/` (brief: `design/qart-flow/BACKEND_BRIEF.md`).*

The six mockups (Profile, Signals, Matches, Pathway, SDG impact, Scenarios) are built on the existing
API. This report lists what the API already covered, what was added (contract v2.1), and what was
**not built because no real data exists**. AGENTS.md forbids inventing statistics, and every mockup
number is illustrative.

## 1. Covered by the existing API (no backend change)

| Screen | Data used |
|---|---|
| Matches | `GET /api/recommendations` (score, fit, factors, formula, gap with evidence states, time_to_ready, sdg_targets, outlook), `GET /api/roles` (title, summary, skills) |
| Pathway | `GET /api/path?role_id=&weekly_hours=` (re-planned per pace), `GET /api/resources/{skill}`, `GET /api/search` |
| Scenarios | two `GET /api/recommendations` calls (assistive, agentic): `outlook.ai_handled_share`, rank per scenario, `changed_since` |
| Signals | `GET /api/snapshots`, `GET /api/snapshots/diff`, `POST /api/ingest/run` (historical data replay) |

## 2. Added (contract v2.1, additive, with tests)

1. **`Profile.preferences`**: industry, education, tools, direction, timeframe_months, formats, ai_comfort, notes.
   - **Stored only.** No engine factor reads them yet. A test pins that scores don't change, and the UI says "saved; not used for ranking yet".
   - If the team wants them to count, these are the natural uses (each is a Person A change that would move rankings and golden-journey numbers, so it needs a joint decision):

     | Field | Possible use | Where |
     |---|---|---|
     | `timeframe_months` | planner horizon: weeks budget = months × 4.3 × weekly hours | `src/engine/planner.py` |
     | `direction` | role filter: grow = current role; adjacent = roles sharing ≥1 skill; switch = all | `src/engine/recommend.py` |
     | `formats` | course tie-break by format, once courses carry a format field | `catalogue/courses.json`, planner |
     | `tools`, `ai_comfort` | could pre-fill self-reports, but **self-report is not evidence**, so keep separate | — |
     | `industry`, `education` | context only; no factor | — |
   - `notes` is synthetic demo text, capped at 500 characters, never logged and never sent to an LLM.
2. **`GET /api/sdg`**: target titles, UN links and rationales from `catalogue/sdg_map.json`. Only 4.4, 8.2 and 8.5 exist. The mockup's goals 9, 12, 13 and 16 are not shown, because the catalogue doesn't declare them.
3. **Fix**: a walk-back corrected without help (help 0) returned 500 (`KeyError` in `HELP_PHRASE`). It's now explained as "on a second look, without help".

## 3. Not built: no real data

| Mockup element | Why not | What would be needed |
|---|---|---|
| Signals: "Skill demand in finance & data roles" (+52% AI tools, etc.) | The only external evidence is the Anthropic Economic Index (usage, automation and augmentation share per occupation). There is no job-postings dataset. | A dated, licensed job-postings extract (e.g. a public Malaysian job-board dataset or the OECD/Lightcast aggregates) mapped to our skill IDs, ingested as a new snapshot type with `source`, `release_date`, `url`. |
| Signals: "Top AI themes this month" (research & news clusters) | No research/news feed exists. | A dated, licensed corpus (e.g. an arXiv category listing) plus a clustering step, recorded in DECLARATION_LOG. Labelled synthetic if it's a demo. |
| Signals: "Open skills taxonomy" source card | The skill taxonomy is our own catalogue (O*NET task statements are already cited per role). | Nothing, unless we adopt e.g. ESCO; then cite it with its licence. |
| Matches: score "84/100 ± 5" | The engine returns a 0–1 suitability indicator, not a probability, with no uncertainty band. | Shown as the real `fit`/`score` with factors and formula. A band would need a sensitivity run (e.g. ±20% weights, as in the close-match check) exposed by the API. |
| Pathway: "HRD Corp claimable" programme, "[Training provider]" | No verified claimable course in `catalogue/courses.json`. | A verified HRD Corp listing added to the catalogue with source and date. Until then, no badge. |
| Scenarios: "30–45% / 50–70% of tasks could be automated" | No ranges exist. | Shown instead as `outlook.ai_handled_share` per scenario: a point value derived from company assumptions (layer B), labelled assumption, with `because` and `basis`. |
| Scenarios: "0–100 demand index, middle 80% of runs" | No simulation or demand index exists. | A Person A addition: a seeded Monte Carlo over the assumption shares, returning percentile bands. Until then, the outlook bars show point values. |
| Scenarios: "Moderate / Fast AI disruption" | The contract enum is `assistive` / `agentic`. | UI labels: "AI helps with routine work" / "AI does most routine work". |

## 4. Rules kept on every screen

- Every number shows a source and date, or an assumption/synthetic label.
- No mastery percentages.
- Personas come from `useUserId()`; no hard-coded user or case ids.
- The practice loop (golden journey) still starts from Start → "Or start practising now".
