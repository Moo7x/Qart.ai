# Evaluation scaffold (`eval/runner.py`, `eval/acceptance_criteria.py`, `eval/acceptance/`)

## 1. What it does
Runs the companion's automatic diagnosis on the acceptance cases, grades it with fixed criteria and
writes counts to `eval/RESULTS.md`, next to a text-only baseline. Today both diagnosers are stubs,
so it honestly reports "not run".

## 2. Why it exists
Increment 3 ("trust numbers") and the improvement gate (PROJECT_PLAN §7): playbook changes are only
accepted after fixed acceptance tests. Numbers go into the PRD as counts, never rounded up.

## 3. How it works
- Criteria (*declared*, fixed, hashed): root cause correct (has_issue and issue types match),
  decision correct, **false alarm** on clean cases, **invalid citations** (rows cited that do not
  exist in the case). `criteria_hash()` = SHA-256 of the criteria file (line endings normalised).
- `load_auto_diagnose()` imports B's `src/companion/auto.py::auto_diagnose(case, playbook_path)`
  when it exists; otherwise `auto_diagnose_not_available` raises NotImplementedError.
- `text_only_baseline_not_built` is the baseline stub: it will give the same LLM the raw tables
  without tools, through a provider-agnostic client (no LLM is called yet).
- Each script writes its own section of `eval/RESULTS.md` (`write_section`).

## 4. Where in the code
`eval/runner.py::run, evaluate, render`, `eval/acceptance_criteria.py::grade, criteria_hash`,
`eval/results_md.py::write_section`. Tests: `tests/test_eval_runner.py`.

## 5. Example
A "flag everything" diagnoser on a clean case: false alarm = 1, root cause wrong, and citing a
non-existent row "X99" counts one invalid citation. A perfect diagnoser on one issue case and one
clean case: root cause 2/2, decision 2/2, false alarms 0/1, invalid citations 0.

## 6. Limits and honesty
No acceptance cases exist yet (B authors them); no numbers are reported until they do. The set
must be run once per candidate, or it stops being an acceptance set.

## 7. Likely judge questions
- *How do you know the companion works?* Counts on independent acceptance cases vs a text-only
  baseline, including false alarms on clean cases.
- *Could you tune to the test?* The optimiser cannot read the folder or the criteria (hash shown).

## 8. Design choices considered
LLM-as-judge grading (criteria here are checkable without an LLM); percentages only (counts are
more honest for small sets).
