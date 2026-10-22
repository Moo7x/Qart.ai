# Playbook optimiser (`src/optimizer/`, `eval/gate.py`, `src/companion/playbook_versions.py`)

## 1. What it does
Improves the companion's checking procedure (the playbook) from its own mistakes, and lets a
senior decide whether the improvement goes live. It proposes; it never activates anything itself.

## 2. Why it exists
PROJECT_PLAN §7 (improvement gate) and Task A9. The first scored run showed the companion
escalating errors it could correct (playbook_v1 Step 6). A self-improvement loop that is measured,
reviewable and reversible is the honest way to fix that, instead of hand-tuning against the test.

## 3. How it works
- **Editable scope:** the playbook text only. Grader, evidence rules, cases and criteria are out of
  bounds.
- **Development set** (`loop.development_set`): the 7 practice and check-in cases plus 2 variants of
  each practice case (`eval/variants.py`: shuffled rows, renamed ids, documents and names; same
  answer) = 17 cases. The loop never imports the acceptance or holdout sets (a test checks this).
- **One round** (`loop.optimise`): diagnose every development case with the current text (the
  companion's automatic diagnosis, LLM path, temperature 0) → grade with the fixed criteria → give
  the model the failures (decided vs right decision, issue types, why) → it returns a revised
  procedure and a rationale (strict JSON) → grade the revision on the same cases.
- **Improvement rule** (*declared*): utility = decisions + root causes − 2 × false alarms − invalid
  citations; a revision is kept only if its utility is higher and it adds no false alarms. False
  alarms cost double because they waste reviewer time and erode trust. A revision may at most
  double the text, so it stays a readable procedure. 2 rounds per run.
- **Gate** (`eval/gate.py`): only after the candidate is frozen, the current and candidate texts are
  scored on the 17 acceptance cases once each; regressions = cases the current text decided
  correctly and the candidate does not. Without a development gain the acceptance set is not run
  and the proposal is stored as rejected by the optimiser itself.
- **Proposal** (`pipeline.run_optimizer`): the candidate is saved as the next version
  (`playbook_vN`, in the store and in `src/companion/playbooks/`), not active; the
  `OptimizerProposal` carries the diff, both sets' counts, regressions, rationale and the run log.
- **Decision** (`src/api_optimizer.py`): approve → the candidate becomes the active playbook for the
  companion; reject → nothing changes; rollback → back to `rollback_to`. Every event records the
  version that produced it (`companion_version`).

## 4. Where in the code
`src/optimizer/loop.py` (development set, scoring, proposer, loop), `src/optimizer/pipeline.py`
(proposal), `src/optimizer/jobs.py` (background run), `eval/gate.py` (acceptance gate),
`src/companion/playbook_versions.py` (versions, active version), `src/api_optimizer.py` (routes),
`web/src/pages/CompanionUpdates.tsx` (senior page). Tests: `tests/test_optimizer.py`,
`tests/test_playbook_versions.py`.

## 5. Example
playbook_v1 on the development set: see the proposal's "Development set before" line. A revision
that makes the decision step say when an identifiable error should be corrected rather than
escalated is kept only if it gains decisions without adding false alarms; the senior then sees
the acceptance counts and regressions before approving.

## 6. Limits and honesty
17 development cases and 17 acceptance cases are small: one case moves a count by one. The
proposer is an LLM, so two runs can propose different texts; the scoring calls are at temperature
0. Variants share the practice cases' error types, so a gain there may not transfer; that is what
the acceptance gate and its regressions are for. A run costs roughly 60–110 LLM calls.

## 7. Questions and answers
- *Can it overfit the test?* It never sees the acceptance cases; they are scored once per
  candidate, after the text is fixed, and the criteria file is hashed.
- *Who is accountable?* A senior approves each version; the version is in every event; rollback
  is one click.
- *Why not GEPA?* A simple reflective loop was enough to show the full cycle and is easy to explain;
  GEPA could replace `optimise` behind the same interface.

## 8. Design choices considered
Letting the optimiser auto-activate (rejected: humans decide); optimising on the acceptance set
(rejected: it would stop being a test); fine-tuning a model (out of scope: the playbook is the
only editable part and is human-readable).
