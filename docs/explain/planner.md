# Learning path planner (`src/engine/planner.py`)

## 1. What it does
Builds an ordered, time-estimated learning path toward one internal role within the employee's
weekly hours, using free courses, in-app practice bundles and confirmation check-ins. The path is
**robust**: it minimises the worst remaining gap across both AI-adoption scenarios.

## 2. Why it exists
Must-have 4 (ordered, time-estimated free path) and 5 (SDG tags per step). Golden journey step 5: the
path visibly changes when evidence arrives.

## 3. How it works
- Resources: practice bundle (3 cases, 1.5 h, *assumption*) per practised skill not yet demonstrated;
  **confirmation check-in** (0.5 h) instead of the bundle when a skill has 1 of 2 independent
  successes; every **verified** course (unverified ones are never recommended).
- Gap per scenario: g = max(0, 1 − credit(state) − Σ gain); gain 0.3 per covering resource
  (*assumption*: coverage ≠ demonstrated skill until new case evidence), 0.5 for a check-in.
- Objective: minimise max over {assistive, agentic} of Σ w·g (w = requirement-card weights).
- Budget: weekly_hours × 6 weeks (*declared*). Prerequisites are added with the course that needs them.
- Greedy: repeatedly add the affordable item that cuts the worst-case gap most per hour (tie: total
  gap cut per hour, then id). Order: prerequisites first, then standalone gap cut per hour.

## 4. Where in the code
`plan_path()`, `build_resources()`, `greedy_select()`, `worst_case_gap()`, `order_steps()`.
Exact version: `src/engine/planner_cpsat.py::cpsat_select` (OR-Tools CP-SAT, same model, values
scaled to integers), passed as `plan_path(..., selector=cpsat_select)`. The API uses greedy (easier
to explain step by step). Tests: `tests/test_path_and_next_case.py` (CP-SAT is never worse than
greedy and respects budget and prerequisites).

## 5. Example (Aina → AI Finance Operations Analyst, 4 h/week)
Before evidence: step 2 is the "Challenge unsupported adjustments: 3 practice cases" bundle. After
case_003 → case_006 → checkin_001 it is replaced by **"Confirmation check-in: Challenge unsupported
adjustments (later session)" (checkin_002, 0.5 h)**, which moves to step 1, and the worst-case gap
drops (greedy 0.64 → 0.57; CP-SAT 0.62 → 0.56). At 1 h/week the plan shrinks to 4 steps.

## 6. Limits and honesty
Gains are assumptions, not measured learning. Greedy is not guaranteed optimal (CP-SAT is, for
the scaled model; differences on Aina's data are ≤ 0.02). Hours for some
courses are estimates (`hours_source` in courses.json).

## 7. Likely judge questions
- *Why a check-in instead of more teaching?* She already succeeded once without help; what is missing
  is evidence, not instruction.
- *What does "robust" mean?* We don't know which AI future the company gets, so we minimise the worse
  of the two gaps.
- *Are the courses real?* Yes, verified URLs with retrieval dates; unverified items are excluded.

## 8. Design choices considered
CP-SAT as the default (exact, but its choices are harder to narrate); LLM-generated plans (not reproducible; could
invent courses).
