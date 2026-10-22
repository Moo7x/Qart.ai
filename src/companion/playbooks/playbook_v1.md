# Companion Checking Procedure v1

Follow these steps in order when reviewing an AI-prepared bank reconciliation.

## Step 1 – Recompute totals
Call `recompute_totals`. If the ledger and bank totals disagree (after adjustments), something is wrong.

## Step 2 – Match every entry
Call `match_entries`. Find which ledger rows correspond to which bank rows. Flag any unmatched entries.

## Step 3 – Challenge every manual adjustment
Call `list_adjustments`. For each adjustment, call `find_document`. If no document supports it, it must be challenged — do not accept "rounding" without evidence.

## Step 4 – Check amounts on matched pairs
For matched rows, call `compare_amounts`. Spot keying errors (e.g. 1,520 vs 1,250). A small difference that is "covered" by an adjustment is suspicious.

## Step 5 – Review the AI's claim
Does the evidence support the AI's conclusion? Ask: "What evidence would make me change this conclusion?" Flag false alarms (AI says error when there is none) and missed errors (AI says OK when there is a problem).

## Step 6 – Decide
- **Sign off** only if every item is matched, supported and amounts are correct.
- **Correct** if you can identify and fix the error yourself.
- **Escalate** if there is an unexplained or unsupported item you cannot resolve alone.

## Rules
- Never claim certainty you don't have.
- Only cite row IDs and amounts that exist in the case.
- If a document exists, cite it. If it doesn't, say so.
