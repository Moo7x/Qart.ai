# Next-case targeting (`src/engine/next_case.py`)

## 1. What it does
Chooses the employee's next case and says why ("You missed … in case_003 …").

## 2. Why it exists
The product promise: *your mistakes are your future skills*. Golden journey steps 3–4: after a miss,
targeted practice; after a helped success, a no-help check-in.

## 3. How it works
1. **Tier 1**: skills with an unresolved miss *and* a help-assisted success since it → close the loop
   with a check-in now. **Tier 2**: other unresolved misses. **Tier 3**: all practised skills.
2. Within a tier: highest w·(1 − credit(state)) for the target role (the user's top-ranked role
   unless given); ties by the internal estimate's uncertainty p(1−p), then id.
3. Case: unseen cases containing the skill; prefer check-in if there is a helped success since the
   miss, else practice; then matching scenario variant, lower difficulty, id.
Case metadata comes from Person B's `cases/index.json` (id, mode, difficulty, scenario_variant,
practised_skills) when it exists, else from the planned `data/case_index.json`; only the grader may
read `ground_truth` (CONTRACT_QUESTIONS Q4). Practised skills are never shown to the employee before
a decision: they would give the answer away.

## 4. Where in the code
`next_case()`, `unresolved_miss()`, `helped_success_since_miss()`, `choose_case()`.

## 5. Example (Aina, assistive)
intake → case_001 (largest gap: AI output review) · after case_003 → **case_006** ("You missed
'Challenge unsupported adjustments' in case_003, then found it after a hint") · after case_006 →
**checkin_001** · after checkin_001 → case_009 (the transposition miss from case_003 moves up).

## 6. Limits and honesty
Until B publishes cases/index.json the planned index is used. The estimate only breaks ties.

## 7. Questions and answers
- *Isn't this just random practice?* No: the rule is deterministic and explained in `because`.
- *Why not repeat the same case?* A repeat tests memory, not the skill; demonstrated requires
  different cases.

## 8. Design choices considered
Bandit/RL selection (needs data, hard to explain); always the weakest skill (ignores the employee's
own recent mistakes, which is the core idea).
