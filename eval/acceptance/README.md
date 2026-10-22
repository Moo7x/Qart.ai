# Acceptance set (independently authored cases from Person B)

This folder holds the **acceptance cases**: independently authored reconciliation cases with
different error mechanisms and case structures from the practice cases (PROJECT_PLAN §7). They are
not variants of practice cases.

Rules (AGENTS.md):
- The optimiser never reads this folder and never changes `eval/acceptance_criteria.py`.
- Each playbook candidate is run against this set **once** (`python -m eval.runner`). If results
  here start guiding changes, the set has become development data: move it to optimisation and
  report numbers from the final untouched set instead.
- Results are reported as counts on synthetic cases in `eval/RESULTS.md`.

Format: one `<case_id>.json` per case in the contract Case format, including `ground_truth`
(only the grader and the evaluation runner read it). Person B authors the cases; Person A runs them.

Status (2026-10-21): empty, waiting for Person B's cases.
