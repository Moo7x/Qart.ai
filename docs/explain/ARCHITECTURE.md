# Qart.ai architecture (one page)

## Data flows
```
Future-role reasoning (Person A)
  layer A  external evidence: AEI snapshots (data/snapshots, dated, CC-BY)
       │  POST /api/ingest/run → diff() → suggested_assumption_reviews   (never changes weights)
       ▼
  layer B  company assumptions (catalogue v1 → store versions; PUT /api/assumptions = HR approval)
       │  task allocation per scenario + shift rule (50% assistive / 80% agentic)
       ▼
  requirement card: O*NET tasks → allocation → skill weights → "because"
       │
  layer C  employee evidence: SkillStates from events (rules, not percentages)
       ▼
  recommend(): 0.55·coverage + 0.20·confidence + 0.10·interest − 0.15·effort  (+ changed_since)
       +  outlook per role (AI-handled / oversight share), fit, time_to_ready, close_match
       ▼
  path planner (weekly hours × 6, prerequisites, min worst-case gap over both scenarios) · next_case

Practice loop (Person B → Person A)
  case → companion (stepped help) → grader (only reader of ground_truth) → Event
       → POST /api/events → evidence rules → SkillState (state, why, evidence_trail)
       → next_case (your latest mistake first) and a revised path
HR: GET /api/hr/summary → counts per state per skill, groups/cells < 5 suppressed, no names
```

## Modules and owners
| Module | Owner | Explanation doc |
|---|---|---|
| `src/contract.py`, `schemas/examples/`, `src/engine/params.py` | both / A | [contract_and_params.md](contract_and_params.md) |
| `catalogue/`, `src/engine/catalogue.py` | A | [catalogue.md](catalogue.md) |
| `src/engine/skills.py` (evidence rules) | A | [skills.md](skills.md) |
| `src/engine/requirements.py` (requirement card) | A | [requirements.md](requirements.md) |
| `src/engine/recommend.py`, `eval/sensitivity.py` | A | [recommend.md](recommend.md) |
| `src/engine/next_case.py`, `data/case_index.json` | A | [next_case.md](next_case.md) |
| `src/engine/planner.py`, `src/engine/planner_cpsat.py` | A | [planner.md](planner.md) |
| `src/engine/snapshots.py`, `src/engine/ingest.py`, `data/snapshots/` | A | [snapshots.md](snapshots.md) |
| `src/engine/hr.py` (aggregates only) | A | [hr.md](hr.md) |
| `src/api_engine.py`, `src/store.py`, `data/synthetic_team.json` | A | [api_engine.md](api_engine.md) |
| `eval/runner.py`, `eval/acceptance_criteria.py`, `eval/acceptance/` | A | [evaluation.md](evaluation.md) |
| `src/retrieval/` (BM25 baseline, RunPod interfaces, corpus), `eval/retrieval_eval.py` | A | [retrieval.md](retrieval.md) |
| `src/main.py` (app: engine router, B's router and web/dist when present) | both | this page |
| `src/companion/`, `src/api_companion.py`, `cases/`, `web/` | B | B's docs |

Engine modules are pure functions (no FastAPI, no DB); `ingest.py`, `src/retrieval/corpus.py` and
`src/retrieval/mslearn.py` are the only ones doing I/O (download, CSV, files). Retrieval is not yet
used by the planner or any endpoint. Routes validate, call the engine and return contract models.

## Labelling rule
Every number is **evidence** (dated source), **assumption** (company layer B or a declared parameter
in `params.py`) or **synthetic** (demo employees, cases, events).
