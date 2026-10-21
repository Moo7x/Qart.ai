# Engine API and store (`src/api_engine.py`, `src/store.py`, `data/synthetic_team.json`)

## 1. What it does
Exposes the engine over HTTP (all Person-A endpoints of contract §5) and keeps profiles, events,
assumption versions, ingested snapshots and optimiser proposals in a database seeded with 12
synthetic employees on first start: **Postgres when `DATABASE_URL` is set** (Replit's built-in
Postgres, used for deployment) and a **SQLite file** otherwise (local runs and all tests).

## 2. Why it exists
B's web app and companion call these routes; the golden journey runs through them. Replit may wipe
local files on redeploy, so the store re-seeds itself when empty.

## 3. How it works
| Route | Does |
|---|---|
| `POST /api/profile`, `GET /api/profile/{id}` | store a profile → initial SkillStates |
| `GET /api/skills/{user}` | SkillState for all 16 skills |
| `POST /api/events` | validate (known user/skills, check-ins help 0, no duplicate id) → store → SkillStates |
| `POST /api/events/{id}/flag` | set companion_error / ambiguous_case / data_issue → event stops counting |
| `GET /api/snapshots`, `GET /api/snapshots/diff?from=&to=` | ingested snapshots; readable diff + suggested reviews |
| `POST /api/ingest/run` | ingest the next dated snapshot (historical replay); optional rebuild from raw |
| `GET /api/roles`, `GET /api/recommendations/{user}?scenario=&snapshot=` | roles; ranking + card + `changed_since` |
| `GET /api/path/{user}?role_id=&weekly_hours=` | robust path (default role: best worst-case score) |
| `GET /api/next-case/{user}?scenario=` | next case + because |
| `GET /api/hr/summary?team=&scenario=` | aggregates only, groups/cells < 5 suppressed |
| `GET/PUT /api/assumptions` | layer B; PUT = HR approval, server bumps the version |
| `GET /api/optimizer/proposals`, `POST …/{id}/decision` | stub store; empty until the optimiser exists |
| `POST /api/demo/reset` | back to seed: v1 assumptions, April snapshot only, Aina without events |

`changed_since`: the store logs every event, flag, assumption version and snapshot in a `changes`
table (server-side order, not client clocks). The recommendation is recomputed **just before the
latest change**: before the latest *session's* events (one check-in alone may not move a factor),
before the flag, or with the previous assumption version, and every moved role gets a reason.

Backend: `select_backend(env)` picks Postgres if `DATABASE_URL` is non-empty, else SQLite at
`QART_DB_PATH`. The SQL is shared ("?" placeholders converted to "%s" for psycopg, portable
`ON CONFLICT` upserts, an explicit `seq` column instead of SQLite's rowid). Seeding an empty
database is wrapped in a Postgres advisory lock so two instances starting together don't both seed.

## 4. Where in the code
Routes in `src/api_engine.py` (`compute_changed_since`, `robust_top_role`); persistence in
`src/store.py` (`Store`, `select_backend`, `make_store`, `seed_demo`, `expand_history`); HR maths in `src/engine/hr.py`. Tests:
`tests/test_api.py` (golden journey steps 2–6 over HTTP), `tests/conftest.py` (fresh DB per test).

## 5. Example
Post Aina's three fixture events → `GET /api/next-case/u_aina` moved case_006 → checkin_001 → case_009;
path swaps the adjustments bundle for checkin_002; `POST /api/ingest/run` → May 2026 snapshot →
diff suggests `assistive.check_entries` → `PUT /api/assumptions` (HR) → v2 → recon_associate's card
shows "Check postings… is drafted by AI and reviewed by a human" and its score moves 0.07 → 0.08.

## 6. Limits and honesty
No authentication (synthetic demo accounts only). HR suppression reduces but does not eliminate
re-identification risk. The optimiser endpoints are a stub and invent no results.

## 7. Questions and answers
- *Can HR see Aina's results?* No; only counts per state, small cells hidden, no names or ids.
- *What happens when new data arrives?* Ingest → diff → suggested review → human approval → new
  version → recompute; ingesting alone changes nothing (tested).
- *Where is the data stored?* Replit Postgres in deployment, a local SQLite file otherwise; both
  re-seed from synthetic JSON when empty.

## 8. Design choices considered
SQLite only (Replit deployments don't keep runtime files reliably and may run several instances);
an ORM such as SQLAlchemy (more code than six small tables need); event sourcing for everything
(the small `changes` log gives the same explanation with less code).
