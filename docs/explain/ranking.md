# Role ranking (`src/engine/ranking.py`)

## 1. What it does
It ranks the 15 future roles for one person. Each role gets a 0–100 score and a band: **Strong match** (75 or more), **Good match** (55–74) or **Stretch** (under 55). It also lists the skills the person has and lacks, two or three plain-language reasons, and flags.

## 2. Why it exists
Domain 1 must-have 3: "rank suitable future roles with an explainable match score and a clear skills gap". The score is one pure function (no AI model, no network, no randomness), so it can always be explained and repeated.

## 3. How it works
There are four components, each from 0 to 1:
- **Skill.** How much of the role's weighted skills you have. Your level is divided by the level the role needs (0.7, "use sometimes"), capped at 1, and core skills count three times as much as nice-to-haves.
- **Momentum.** The radar labels of the role's tracked core skills: Rising 1, Stable 0.5, Cooling 0. With no tracked core skill it is a neutral 0.5, and a reason says so. **This is where the trend data feeds the ranking:** a new snapshot changes it.
- **Direction.** Your answer (grow / nearby / switch) against the role's family: same family, adjacent family, or far. Matching your industry adds 0.1. For a nearby move, a different role in your own family scores 0.9 (team decision on persona p1; the spec had 0.6).
- **Feasibility.** Your weekly hours × weeks in your timeframe (3, 6 or 12 months = 13, 26 or 52 weeks), divided by the hours to close the gap, capped at 1.

**Score:** 100 × the weighted sum.
- For grow and nearby, the weights are skill 0.5, momentum 0.2, direction 0.2, feasibility 0.1.
- For switch they are 0.35 / 0.30 / 0.20 / 0.15.

**Guards:**
- With under half of a role's core weight, the role is capped at 54, so it is shown as a Stretch.
- With fewer than 3 skills you get starter roles, not a ranking.
- Ties break on momentum, then name.

**Inputs:** your skills are the questionnaire levels, raised by practice evidence. Gap hours come from each skill's `learn_hours`.

**Fairness:** education, age, years of experience and free text never enter a component. Education only adds a note ("Often asks for a bachelor's degree"). A test pins this.

## 4. Where in the code
- `catalogue/scoring.json`: all weights and thresholds.
- `src/engine/ranking.py`: `rank_roles` (pure), `score_role`, `hours_between`, plus `rank_for_profile`, which loads the inputs.
- Tests:
  - `tests/test_ranking.py`: hand-calculated components, the cap, ties, the empty profile, the trend swap, fairness.
  - `tests/test_personas.py` and `tests/personas/`: the six personas, run against pinned radar labels. All six pass.

## 5. Example
Persona p1 is a Reconciliation Associate making a nearby move, 6 months at 3 h/week. Finance Data Analyst scores **70 (Good match)**:
- skill 0.60: 3 of 4 core skills;
- momentum 0.50: its tracked core skill, SQL, is Stable;
- direction 1.0: analytics is adjacent to finance operations;
- feasibility 1.0: the gap is about 62 h and the plan has 78 h.

## 6. Limits
- The weights are declared choices, not learned.
- Momentum comes from one tech-heavy job board, so finance and marketing skills are mostly "insufficient data" and those roles sit at a neutral 0.5.
- `learn_hours` are team estimates.

## 7. Questions and answers
- *Why not machine learning?* There is no labelled data to validate it, and it would hurt explainability (spec §0).
- *Does a higher number always mean better?* Bands come first. 73 vs 71 is not a meaningful difference.
- *Can the trend data change my matches?* Yes, through momentum. That is the point, and a test shows it.
