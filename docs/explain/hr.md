# HR aggregate summary (`src/engine/hr.py`)

## 1. What it does
Gives HR/L&D counts of people per evidence state for each skill, and training demand per AI-adoption
scenario, for a team. Never names, ids, individual scores or "who should move where".

## 2. Why it exists
AGENTS.md: "HR sees aggregates only (groups under 5 suppressed)". HR plans training capacity, not
headcount cuts; individual recommendations stay with the employee.

## 3. How it works (*declared* thresholds in `params.py`)
- Group < 5 people → only a suppression notice.
- Cell (people in one state for one skill) of 1–4 → `null`. If exactly one cell in a row is hidden,
  the smallest other cell is hidden too (otherwise group size minus the others reveals it).
- Training demand: per scenario, skills that some internal role weights ≥ 0.05 there, with the number
  of people who have not demonstrated them (also suppressed under 5).

## 4. Where in the code
`hr_summary()`, `suppress_row()`; route `GET /api/hr/summary?team=&scenario=`. Tests in
`tests/test_api.py::test_hr_summary_is_aggregate_only_and_suppresses_small_groups`.

## 5. Example
`team=finops_kl` (9 synthetic people): most cells show `null` because few people share a state;
`team=ap_penang` (3 people) is fully suppressed.

## 6. Limits and honesty
Suppression reduces but does not eliminate re-identification risk (e.g. combining queries over time).
With 9 people most cells are hidden: that is the honest cost of privacy at this size.

## 7. Questions and answers
- *Why not show HR who is ready?* That turns a learning tool into a selection tool; humans decide,
  and employees own their record.
- *Why 5?* A common small-cell rule; declared, not derived.

## 8. Design choices considered
Differential privacy noise (hard to explain at n=9 and distorts small counts); k-anonymity on
multiple attributes (we only release one attribute per cell).
