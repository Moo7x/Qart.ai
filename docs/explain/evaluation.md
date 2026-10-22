# Evaluation (`eval/runner.py`, `eval/baseline.py`, `eval/acceptance_criteria.py`, `eval/acceptance/`)

## 1. What it does
Runs three diagnosers on the 17 acceptance cases, grades them with fixed criteria and writes counts
to `eval/RESULTS.md`:
- **companion, rules only**: `auto_diagnose(..., use_llm=False)`, deterministic checks only;
- **companion, LLM**: the model gets the playbook (the checking procedure) and the tool results
  (recomputed totals, matched rows, adjustments);
- **text-only baseline**: the same model gets only the raw case, with no playbook and no tools.

## 2. Why it exists
Increment 3 ("trust numbers") and the improvement gate (PROJECT_PLAN §7): a playbook change is
accepted only after fixed acceptance tests. The baseline answers the judges' question "does your
companion beat just asking the model?". Numbers go into the PRD as counts, never rounded up.

## 3. How it works
- Criteria (*declared*, fixed, hashed): root cause correct (has_issue and issue types match),
  decision correct, **false alarm** on clean cases, **invalid citations** (rows cited that do not
  exist in the case). `criteria_hash()` = SHA-256 of the criteria file (line endings normalised).
- Both LLM diagnosers use one call (`src/companion/auto.py::llm_diagnosis`): a strict JSON schema
  whose labels are the error-type skill ids and whose rows are the ids in that case, temperature 0,
  answer cleaned again in code. They differ only in what the model is given.
- The **Note** column counts answers whose `source` is `llm`, so a silent fallback to rules can
  never pass as an LLM result. Without `LLM_API_KEY` the LLM rows say "not run".
- The acceptance set is run **once per playbook version**. Development and the optimiser use the
  practice cases and `eval/variants.py` output; `eval/holdout/` stays untouched for final numbers.

## 4. Where in the code
`eval/runner.py::run, default_diagnosers, evaluate, render`, `eval/baseline.py::text_only_baseline`,
`eval/acceptance_criteria.py::grade, criteria_hash`, `eval/results_md.py::write_section`.
Tests: `tests/test_eval_runner.py`, `tests/test_auto_diagnose.py`.

## 5. Example
First scored run (playbook_v1, gpt-4o-mini, 17 cases, 5 clean): decisions correct 6/17 (rules),
6/17 (LLM companion), 14/17 (text-only baseline); false alarms 2/5, 2/5, 0/5. On the practice
cases the companion escalates errors that can be fixed (case_002 duplicate, case_003
transposition) because Step 6 of playbook_v1 says to escalate any unsupported item, while the
baseline misses real escalations (case_006, checkin_002).

## 6. Limits and honesty
17 synthetic cases is a small set: one case moves a count by one. The baseline currently scores
higher than the companion; we report that instead of hiding it. Improving the playbook is the
optimiser's job (Task A9), measured on the optimisation set and only then scored here once.

## 7. Questions and answers
- *How do you know the companion works?* Counts on independent acceptance cases vs a text-only
  baseline, including false alarms on clean cases. Today the baseline wins on decisions, and we
  can show why (the playbook's escalation rule).
- *Could you tune to the test?* The optimiser cannot read the folder or the criteria (hash shown),
  and the set is run once per version.

## 8. Design choices considered
LLM-as-judge grading (criteria here are checkable without an LLM); percentages only (counts are
more honest for small sets); a baseline without the schema (it would not be comparable).
