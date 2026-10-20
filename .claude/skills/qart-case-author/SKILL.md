---
name: qart-case-author
description: Author or review a Qart.ai synthetic bank-reconciliation case (cases/*.json) in the contract Case format, with planted errors or a clean/false-alarm design, and verify every number adds up. Use for practice, check-in, real-work and acceptance cases (Person B).
---

# Qart.ai case authoring

## Format
Follow the contract "Case" example exactly: `id, title, mode, difficulty, scenario_variant, ledger[], bank[], documents[], ai_output{claim, proposed_adjustments[]}, ground_truth{has_issue, issue_types[], affected_rows[], correct_decision, explanation, skills[]}`. Currency is MYR; the company is the synthetic **Kopi Kita Sdn Bhd**; all names are fictional.

## Design rules
- 8–15 ledger rows and a similar number of bank rows; one month (October 2026).
- Exactly **one main issue** per practice case (two only for difficulty 3). Issue types come from the skill list: duplicate, transposition, cut-off/timing, unsupported adjustment, FX rate, AI false alarm.
- **Clean cases** must contain realistic noise (timing items with documents) and must reconcile correctly.
- Include **plausible alternative explanations**, e.g. a difference that looks like an error but is a documented deposit in transit.
- The AI's claim must be plausible and confidently worded (e.g. "Reconciles after rounding adjustment").
- Acceptance cases must use **different reasoning patterns and structures** from practice cases (bank-side error, split payment, reversed entry, offsetting errors, partial FX payment). They are never variants of practice cases.

## Verification (do all, with code, before saving)
1. Recompute: ledger closing balance, bank closing balance, sum of reconciling items, sum of proposed adjustments.
2. Check that the stated difference and the AI claim follow from the numbers as designed, and that the ground-truth explanation is arithmetically true.
3. Every `doc_ref` in the ledger exists in `documents`. Every row in `affected_rows` exists.
4. For clean cases: the reconciliation balances with the documented items, and `correct_decision` = `sign_off`.
5. Print a one-paragraph human summary of the case for the reviewer (a finance/accounting person, if available).

Save to `cases/<id>.json`. Acceptance cases go to `eval/acceptance/` (hand to Person A) and are never used for practice.
