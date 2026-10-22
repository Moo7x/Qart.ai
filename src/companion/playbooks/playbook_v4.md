# Companion Checking Procedure v2

Follow these steps in order when reviewing an AI-prepared bank reconciliation.

## Step 1 – Recompute totals
Call `recompute_totals`. If the ledger and bank totals disagree (after adjustments), something is wrong. Investigate any discrepancies before proceeding.

## Step 2 – Match every entry
Call `match_entries`. Find which ledger rows correspond to which bank rows. Flag any unmatched entries. Verify if unmatched entries are legitimate, such as deposits in transit, before flagging them as issues.

## Step 3 – Challenge every manual adjustment
Call `list_adjustments`. For each adjustment, call `find_document`. If no document supports it, it must be challenged — do not accept "rounding" without evidence. Ensure adjustments do not hide potential errors like duplicates or transpositions.

## Step 4 – Check amounts on matched pairs
For matched rows, call `compare_amounts`. Spot keying errors (e.g. 1,520 vs 1,250). A small difference that is "covered" by an adjustment is suspicious. Consider transposition errors and verify if the adjustment is valid.

## Step 5 – Review the AI's claim
Does the evidence support the AI's conclusion? Ask: "What evidence would make me change this conclusion?" Flag false alarms (AI says error when there is none) and missed errors (AI says OK when there is a problem). Verify the context of unmatched entries, especially deposits in transit, before deciding.

## Step 6 – Decide
- **Sign off** if every item is matched, supported, amounts are correct, and any unmatched entries are justified (e.g., deposits in transit).
- **Correct** if you identify errors such as duplicates or transpositions that can be resolved by removing or adjusting entries.
- **Escalate** if there is an unexplained or unsupported item you cannot resolve alone, and it does not fit known legitimate cases like deposits in transit.

## Rules
- Never claim certainty you don't have.
- Only cite row IDs and amounts that exist in the case.
- If a document exists, cite it. If it doesn't, say so.