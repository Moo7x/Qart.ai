# Qart.ai architecture (one page)

## Data flows
```
Future-role reasoning (Person A)
  layer A  external evidence: AEI snapshots (data/snapshots, dated, CC-BY)
       │  diff() → suggested_assumption_reviews   (never changes weights directly)
       ▼
  layer B  company assumptions (catalogue v1 → store versions; HR approves, version bumps)
       │  task allocation per scenario + shift rule
       ▼
  role requirement card (O*NET tasks → allocation → skill weights → "because")
       │
  layer C  employee evidence: SkillStates from events (rules, not percentages)
       ▼
  recommend(): 0.55·coverage + 0.20·confidence + 0.10·interest − 0.15·effort
       ▼
  path planner (weekly hours, prerequisites, robust across both scenarios) · next_case

Practice loop (Person B → Person A)
  case → companion (stepped help) → grader (only reader of ground_truth) → Event
       → POST /api/events → evidence rules → SkillState (state, why, evidence_trail)
```

## Modules and owners
| Module | Owner | Explanation doc |
|---|---|---|
| `src/contract.py`, `schemas/examples/` | both | (contract) |
| `src/engine/params.py` | A | every module doc cites it |
| `catalogue/`, `src/engine/catalogue.py` | A | [catalogue.md](catalogue.md) |
| `src/engine/skills.py` (evidence rules) | A | [skills.md](skills.md) |
| `src/engine/requirements.py` (requirement card) | A | [requirements.md](requirements.md) |
| `src/engine/recommend.py`, `eval/sensitivity.py` | A | [recommend.md](recommend.md) |
| `src/engine/next_case.py`, `data/case_index.json` | A | [next_case.md](next_case.md) |
| `src/engine/planner.py` (greedy robust path) | A | [planner.md](planner.md) |
| `src/engine/snapshots.py`, `src/engine/ingest.py`, `data/snapshots/` | A | [snapshots.md](snapshots.md) |
| `src/main.py` (app skeleton) | both | this page |
| `src/api_engine.py`, `src/store.py` | A | added in Step 6 |
| `src/companion/`, `src/api_companion.py`, `cases/`, `web/` | B | B's docs |

## Labelling rule
Every number is **evidence** (dated source), **assumption** (company layer B or a declared parameter
in `params.py`) or **synthetic** (demo employees, cases, events).
