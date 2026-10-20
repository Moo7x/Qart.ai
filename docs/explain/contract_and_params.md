# Contract models and parameters (`src/contract.py`, `schemas/examples/`, `src/engine/params.py`)

## 1. What it does
`src/contract.py` holds one Pydantic model per contract object (Profile, Case, Event, SkillState,
Role, Snapshot, CompanyAssumptions, Recommendation, PathPlan, Course, OptimizerProposal) plus small
responses (NextCase, SnapshotDiff). `params.py` holds every weight and threshold the engine uses.

## 2. Why it exists
Both teammates build against the same JSON (contract §4). Judges ask "where does this number come
from?": every number lives in one file with its status.

## 3. How it works
- `schemas/examples/*.json` are the contract examples copied verbatim; `tests/test_contract.py`
  validates each against its model, and `tests/test_contract_outputs.py` checks that real endpoint
  output contains every example field.
- Fields we added are **optional**, so the examples stay valid; each is listed in
  `docs/CONTRACT_QUESTIONS.md` (Q2) for both teammates to confirm.
- `params.py` labels each constant DECLARED (team design choice), ASSUMPTION (provisional, no data)
  or SOURCED. Company adoption assumptions are *not* there: they are layer B in
  `catalogue/company_assumptions.json`, edited by HR.

## 4. Where in the code
`src/contract.py` (enums `HelpLevel`, `Scenario`, `Outcome`, `Allocation`…), `src/engine/params.py`.

## 5. Example
`RankChange` serialises its `from_rank` field as `"from"` (a Python keyword), exactly as in the
contract's `changed_since.rank_changes`.

## 6. Limits and honesty
`outcome: "failure"` and several optional fields are our proposals until agreed at C1 (Q1, Q2).

## 7. Likely judge questions
- *Why Pydantic?* Validation at the API boundary and one source of truth for the JSON shape.
- *Are your weights tuned?* No; they are declared and tested for ±20% sensitivity.

## 8. Design choices considered
JSON Schema files only (no runtime validation in Python); generating models from schemas (extra
tooling for 11 objects).
