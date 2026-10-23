# Personal journey

**What and why.** A synthetic CV or questionnaire becomes editable skill claims, scores for all
nine GBS destinations, a person-chosen goal and an ordered free-resource pathway (must-haves
1, 3–6). `src/intake/` scrubs identifiers and checks model quotes; missing services use labelled
keyword/form fallbacks. `src/pack.py` validates the curated skill, role, resource and SDG pack.

**Calculation.** `src/match/engine.py` computes
`fit = 100 × sum(weight × min(claimed / required, 1)) / sum(weight)`.
Unknown levels contribute zero but remain "not stated"; essential gaps mean "longer route".
Global occupation-level automation-style Claude usage motivates scenario shifts. The transfer
to Malaysian work, levels and weights are declared assumptions, not learned adoption forecasts.
Essentials keep their level and weight. `src/params.py` names each policy value.

`src/pathway/planner.py` visits essentials first, selects the shortest useful course, includes
prerequisites once and schedules at the weekly-hours budget. Duration/level rules produce
hypothetical gains, not measured learning outcomes. Some gaps have no verified free resource.
`src/journey/store.py` persists claims and destination, not the full CV or contact fields.

**Where.** `src/api/journey.py`: intake, pack, profile, matches, destination, pathway and future
routes. `web/src/pages/{Onboarding,Roles,Pathway,Future}.tsx` consume the real API. Pathway
checkboxes are self-reported completion scoped to one profile in this browser; they do not alter
skill claims or fit, and another synthetic profile does not inherit them.

**Example.** A cash application analyst claims reconciliation level 3, chooses four learning
hours a week and selects O2C Reporting Analyst. The planner orders available resources for its
gaps, names uncovered gaps and explains the relevant SDG targets. Switching scenarios changes
nonessential emphasis, never the person's claims or goal.

**Limits and judge questions.** Fit is requirement coverage, not hiring probability. The planner
is greedy, not a proven optimum. Quoted CV evidence does not verify a proficiency level. Scores
and explanations are computed from the same inputs; the LLM cannot invent scores or resources.
There is no collaborative filtering because there is no interaction history. Learning progress
does not prove mastery. The person chooses; Qart makes no hiring decisions.

**Alternatives.** Learned ranking, robust optimisation and sensitivity analysis require measured
comparison and remain deferred. No tutoring, exercises or practice assessment are part of Qart.
