# Recommender (`src/engine/recommend.py`)

## 1. What it does
Ranks the company's internal roles for one employee under one scenario, returning every factor, the
formula, the gap list, the requirement card, sources and `changed_since`.

## 2. Why it exists
Must-have 3 (explainable role score + gap). The success test: profile → ranked roles in minutes, and
visible change when evidence or assumptions change. **Humans decide**: it recommends, never assigns.

## 3. How it works (all weights *declared*, `params.py`)
```
coverage   = Σ w·credit(state) / Σ w        credit 1.0 / 0.5 / 0.2 / 0 (demonstrated / helped / self-reported / none)
confidence = Σ w·[≥2 counted events] / Σ w
interest   = |interests ∩ role tags| / |interests|
effort     = min(1, Σ (1−credit)·hours of the shortest resource / (weekly_hours × 12))   ← penalty
score      = 0.55·coverage + 0.20·confidence + 0.10·interest − 0.15·effort
```
w = scenario weights from the requirement card. Hours: 1.5 h practice bundle for practised skills
(*assumption*), else the shortest verified course. The score is a **suitability indicator, not a
probability**; it can be slightly negative when gaps are large. `changed_since()` compares two
recommendations and gives a reason per moved role (new events, or a new assumption version).

**Readable ranking** (ordering unchanged): the displayed `score` is clamped at 0 and `score_note`
explains the effort penalty; ordering uses the unclamped value. `fit` = (0.55·coverage +
0.20·confidence + 0.10·interest) / 0.85 ∈ [0, 1] (how well the evidence matches, ignoring time).
`time_to_ready` = {hours to close gaps, weeks at the employee's weekly hours}. `close_match` marks the
top two roles when their unclamped scores differ by < 0.03 (*declared*: halfway between the largest
gap that flipped under ±20% in `eval/SENSITIVITY.md` and the smallest that stayed stable; re-derived
after the course update).

## 4. Where in the code
`recommend()`, `score_role()`, `compute_factors()`, `gap_list()`, `changed_since()`,
`top_role_under_sensitivity()`. Tests: `tests/test_recommend.py`. Report: `eval/SENSITIVITY.md`
(`python -m eval.sensitivity`).

## 5. Example (Aina, agentic, v1)
Intake: top role `ai_finops_analyst` (interest 1.0, coverage 0.04). After the golden journey her
evidence on `unsupported_adjustment` lifts `recon_associate` coverage 0.08 → 0.19 and confidence
0 → 0.36; it becomes rank 1 because agentic weights that oversight skill heavily.

## 6. Limits and honesty
Weights are design choices, not fitted. ±20% check: stable after the golden journey (agentic); near
ties at intake flip on interest/effort, so intake rankings are weak signals. Demographic fields are
never read (twin test in `tests/test_recommend.py`).

## 7. Questions and answers
- *Is 0.52 a 52% chance?* No. It is a suitability indicator; the factors are shown.
- *Why is effort subtracted?* Long paths are a real cost to the employee; it is a penalty.
- *What if weights are wrong?* Sensitivity is reported; HR can see every factor.
- *Bias?* No demographic inputs; twin test proves identical ranking.

## 8. Design choices considered
Multiplicative score (hides which factor drives the result); learned ranking (no outcome data;
would invite job-outcome claims we cannot support).
