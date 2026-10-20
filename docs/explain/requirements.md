# Role requirement card (`src/engine/requirements.py`)

## 1. What it does
For one role and one scenario, shows **which tasks the role has** (O\*NET), **who does each task**
under the company's AI-adoption assumptions, the **resulting skill weights**, and **because** for
every weight. It is the bridge from trends to roles that judges will inspect.

## 2. Why it exists
Must-haves 3 (explainable role score) and 6 (two scenarios labelled as estimates). PROJECT_PLAN §6:
external evidence (layer A) informs company assumptions (layer B); weights follow from layer B only.

## 3. How it works (shift rule, *assumption* from `company_assumptions.json`)
1. Base weight = the role's `base_weight` values, normalised to sum to 1 (*declared*).
2. Each skill's base weight is split equally across the role tasks that use it.
3. If the scenario gives a task to `ai_drafts_human_reviews` or `ai`, a fraction **f** of every
   **execution** skill's share in that task moves to the role's **oversight** skills, pro rata to
   their base weights. f = 0.5 (assistive) / 0.8 (agentic).
4. Weight is moved, never created: scenario weights still sum to 1.
Worked example (unit-tested): A (execution, 0.6, in task t) and B (oversight, 0.4). Assistive, t → AI:
A loses 0.5 × 0.6 = 0.3 → A 0.3, B 0.7.

## 4. Where in the code
`scenario_weights()` (the rule), `requirement_card()` (tasks, weights, because, assumption text,
evidence links), `evidence_links()` (AEI signals for the role's SOC codes). Tests:
`tests/test_requirements.py`.

## 5. Example (Aina's top role, agentic, v1)
`recon_associate`: "Reconcile records of bank transactions" → `ai`; "Check figures, postings…" → `ai`;
adjustments → AI drafts. `unsupported_adjustment` rises 0.11 → 0.36 ("oversight skill gains weight
shifted from execution work in tasks the AI drafts or does … (assumption v1)") while `recon_to_source`
falls 0.16 → 0.03 ("'Match ledger entries…' moves to AI … 80% … shifts to oversight skills").

## 6. Limits and honesty
The 50%/80% fractions and the allocation table are synthetic company choices, not findings. Usage of
AI on a task (AEI) is not proof that the task is replaced. Evidence links are context only.

## 7. Likely judge questions
- *How do trends change roles?* Only through HR approving a new assumption version; the card shows
  the version and the evidence that triggered the review.
- *Why move weight instead of adding new skills?* Total importance stays comparable across scenarios.
- *Why execution vs oversight?* It is the simplest explainable model of "doing → checking" work.
- *Can HR break it?* Every change bumps the version and the card shows the new allocation.

## 8. Design choices considered
Learning weights from data (no data on this company); per-task custom shift sizes (harder to explain;
one fraction per scenario is enough for the prototype).
