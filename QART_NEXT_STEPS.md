# Qart.ai — Next Steps: Role Ranking, Questionnaire Changes and Fixes

> Second build spec for Claude Code. It follows `AI_SIGNAL_SPEC.md`.
> **Don't start this file until the AI signal work is finished and its acceptance criteria pass.**
> Before coding: read this whole file, re-read `AI_SIGNAL_SPEC.md`, inspect the current repo (especially the onboarding questionnaire, the skills config, and the pathway generator), then summarise in 5–10 lines what exists and what you'll change. If anything here conflicts with the repo, follow the repo and note the deviation.

---

## 0. Context and decisions already made

- **Goal of this phase:** rank suitable future roles for the user with an **explainable match score** and a **clear skills gap** that feeds the reskilling pathway.
- **No CV upload (for now).** All user information comes from the question-answer onboarding flow. Remove or hide any CV upload entry points, and don't build CV parsing.
- **Data rules (hackathon):**
  - The AI / job-market trend signal uses **real public data** (already built per `AI_SIGNAL_SPEC.md`).
  - User profiles are **self-entered demo data**. They never leave the app or go to any external API.
  - The role catalogue is built from **public datasets** (O\*NET / ESCO) plus team curation, with each role linking to its source code.
- **Principles:**
  1. One shared skill vocabulary across the whole app.
  2. The role catalogue's data quality matters more than the algorithm.
  3. Scoring is one **pure, deterministic function**. No LLM, no network, no randomness.
  4. Explanations are generated from the same numbers as the score, so they can never disagree.
  5. The **skills gap is the main product**. If time runs short, protect the gap list over score polish.
  6. No ML models, learned weights or embedding similarity for scoring. There's no labelled data to validate them, and they'd hurt explainability.

---

## 1. Amendments to `AI_SIGNAL_SPEC.md`

Apply these small changes to the already built AI signal feature:

- **§3 "User skills":** replace the CV skill extraction with: *user skills come from the questionnaire answers (role pre-fill + task mapping + tools chips + skill levels), mapped to canonical skill IDs.*
- **§6.2 Skills Radar:** "the user's CV skills" becomes "the user's skills from onboarding".
- **§6.3 Pathway link:** same input change. It still returns `user_skills_cooling` and `rising_skills_not_in_cv` (rename the latter to `rising_skills_not_held`).
- Remove any remaining "CV" wording in UI copy. The rule "user data never sent to external APIs" stays.

---

## 2. Shared skill vocabulary (do this first)

`config/skills.yaml` (created in the AI signal phase) becomes the **single canonical skill list** for:
the questionnaire, task mapping, tools chips, role catalogue, trend signal, gap list and pathway.

Add these fields to each skill entry if they're missing:

```yaml
- id: sql
  name: SQL
  category: Data
  patterns: [...]            # from AI signal phase, used for HN matching
  learn_hours:               # team estimates to go from one level to the next
    to_basic: 15             # none -> "use sometimes"
    to_confident: 25         # "use sometimes" -> "confident"
  trend_tracked: true        # false if no reliable HN signal (shows "No market data")
```

- Not every skill needs HN patterns. Soft or domain skills (e.g. "reconciliation", "stakeholder communication") can have `trend_tracked: false`.
- **Validation test (required):** every skill ID referenced anywhere (roles, tasks, tools chips, role pre-fill) must exist in `skills.yaml`. Fail the test on any unknown ID.

---

## 3. Questionnaire changes

### 3.1 Role pre-fill (new)
- When the user selects their **Current role**, pre-tick the typical skills for that role from a mapping `config/current_roles.yaml`:
  ```yaml
  - id: reconciliation_associate
    name: Reconciliation Associate
    family: finance_ops
    typical_skills: [excel, reconciliation, erp, attention_to_detail, financial_reporting]
  ```
- Show the pre-filled skills as editable chips: *"We've added skills typical for your role. Remove any you don't use, add any we missed."*
- Pre-filled skills default to the level **"use sometimes"**.

### 3.2 Task question (new)
- Add: **"Which of these do you do most weeks?"** (multi-select, ~8–12 options, filtered or ordered by the current role family where possible).
- Each task maps to one or more skill IDs in `config/tasks.yaml`:
  ```yaml
  - id: build_monthly_reports
    label: Build monthly reports
    skills: [excel, financial_reporting, data_visualisation]
  - id: record_macros
    label: Record or edit Excel macros
    skills: [excel_automation]
  - id: query_database
    label: Pull data from a database
    skills: [sql]
  ```
- Ticking a task adds its skills at level **"use sometimes"**. Don't downgrade a skill the user already set higher.

### 3.3 Skill levels (new, lightweight)
- For each skill the user holds, allow three levels: **Heard of it** (0.3) · **Use sometimes** (0.7) · **Confident** (1.0). The values go in config.
- Only show the level control on the user's skill chips (tap to change). Don't add a separate long grid.

### 3.4 Existing fields — how each is used
| Field | Used for | Badge in UI |
|---|---|---|
| Current role | Role pre-fill, role family for direction fit | — |
| Industry | Small direction-fit bonus (§5.3) | "Shapes your ranking" |
| Highest education | **Soft flag only** ("this role often asks for a degree"). No score effect | "Saved · shown as a note" |
| Years of experience | Explanation text and role level wording (e.g. "Senior"). No score effect in v1 | — |
| Tools you use today | **Core input:** maps to skill IDs | Change to "Shapes your ranking" (remove "not used for ranking yet") |
| Direction (grow / nearby / switch) | Direction fit and weight preset | "Shapes your pathway" (keep) |
| Timeframe | Feasibility | — |
| Weekly hours | Feasibility | — |
| AI comfort | Pathway: ≤3/10 puts an intro-to-AI course first (existing). No ranking effect | keep |
| Preferred format | Pathway content selection only | Badge must say exactly what it does |
| Free text "Anything else" | Saved only. Never sent to the AI companion or any API (existing copy) | keep |

**Rule:** every badge and helper text must truthfully state whether the field affects the ranking, the pathway, or nothing yet.

### 3.5 Keep it short
Aim for ~8–10 questions in total, mostly taps. Keep the existing three-section structure: *Where you are now → Where you want to go → How you learn*.

---

## 4. UI fixes (existing screens)

1. **AI comfort slider shows "not set" while the handle sits mid-track.** Either start the handle at an explicit empty or neutral state with no position until the user interacts, or show the actual value (e.g. "5/10") as soon as it's set. The label and handle must never disagree.
2. **Default timeframe mismatch.** The helper text says that without a timeframe the plan covers **6 weeks**, but the options are 3 / 6 / 12 months. Make the default one of the visible options (**3 months**), pre-select it visibly, and update the helper text to match.
3. **"Tools you use today"** badge: change from "Saved · not used for ranking yet" to reflect that it now drives the ranking.
4. **"Industry and education are saved… ranking does not use them yet"** footnote: update it to match §3.4 (industry gives a small direction bonus; education is a note only).
5. **"None of these" tools chip:** selecting it must clear the other tool chips, and vice versa.
6. Remove any CV upload UI and copy.

---

## 5. Role ranking

### 5.1 Role catalogue — `config/roles.yaml`
About **15 well-curated roles** is the target. Quality over quantity: 5–8 skills per role, honest weights, similar sizes across roles.

```yaml
- id: finance_data_analyst
  name: Finance Data Analyst
  family: analytics
  source: { dataset: "O*NET", code: "15-2051.00" }   # or ESCO URI; must be a real code
  typical_industries: [finance, banking, consulting]
  min_education: bachelor          # for soft flag only
  skills:
    - { id: excel, weight: 3 }        # core
    - { id: sql, weight: 3 }
    - { id: data_visualisation, weight: 3 }
    - { id: financial_reporting, weight: 3 }
    - { id: python, weight: 1 }       # nice to have
    - { id: statistics_basics, weight: 1 }
  required_level: { default: 0.7 }    # level needed to count as "has it"; can override per skill
```

- Weight **3 = core**, **1 = nice to have**.
- **Starting list (team to review and adjust):** Finance Data Analyst, Finance Automation (RPA) Specialist, FP&A Analyst, AI-enabled Accountant / Controller, Risk & Compliance Analyst (RegTech), Business Analyst, Data Analyst, BI Developer, Data Engineer, ML Engineer, AI Operations / Prompt Specialist, AI Product Specialist, Digital Marketing Analyst, Cybersecurity Analyst, Digital Transformation Project Manager.
- **Role family adjacency** in `config/families.yaml`: for each family, list the adjacent families (e.g. `finance_ops` ↔ `analytics`, `finance_ops` ↔ `automation`, `analytics` ↔ `data_engineering`).
- **Claude Code must not invent O\*NET / ESCO codes.** If a code can't be verified, leave `source.code: TODO` and list it in the summary for the team.

### 5.2 Scoring — one pure function

```ts
rankRoles(profile, roles, skillSignals, config) -> RankedRole[]

RankedRole = {
  roleId, score,                  // 0–100 integer
  band,                           // "Strong match" | "Good match" | "Stretch"
  components: { skill, momentum, direction, feasibility },   // each 0–1
  weightsUsed: { ... },
  matchedSkills: [{ skillId, userLevel, requiredLevel }],
  gap: GapItem[],
  reasons: string[],              // 2–3 template sentences
  flags: string[]                 // e.g. "Often asks for a bachelor's degree"
}
```

No I/O, no LLM, no randomness. All weights and thresholds come from `config/scoring.yaml`.

### 5.3 Components (each 0–1)

- **Skill match:**
  `Σ(weight × min(userLevel / requiredLevel, 1)) / Σ(weight)` over the role's skills.
- **Market momentum:** the average over the role's **core** skills with `trend_tracked: true` of Rising = 1, Stable = 0.5, Cooling = 0, using the labels from `skill_signals.json`. If no core skill is tracked, use a neutral 0.5 and add the reason "No market trend data for this role's core skills".
- **Direction fit** (from user direction × role family vs current family):
  | Direction | Same family | Adjacent | Far |
  |---|---|---|---|
  | Grow | 1.0 | 0.4 | 0.0 |
  | Nearby | 0.6 | 1.0 | 0.2 |
  | Switch | 0.2 | 0.7 | 1.0 |
  Plus an industry bonus of +0.1 (capped at 1.0) if the user's industry is in `typical_industries`.
- **Feasibility:** `min(1, availableHours / gapHours)`, where `availableHours = weeklyHours × timeframeWeeks` (3 months = 13 weeks, 6 = 26, 12 = 52). If `gapHours = 0`, the value is 1.

### 5.4 Weight presets (config)
| Direction | skill | momentum | direction | feasibility |
|---|---|---|---|---|
| Grow / Nearby | 0.50 | 0.20 | 0.20 | 0.10 |
| Switch | 0.35 | 0.30 | 0.20 | 0.15 |

`score = round(100 × Σ weight × component)`

### 5.5 Guards (known traps)
- **Core coverage cap:** if the user covers less than 50% of the role's core weight, cap the score at the top of the "Stretch" band. This stops roles with few skills from winning by accident.
- **Bands** (config): Strong ≥ 75, Good 55–74, Stretch < 55. **Rank and display primarily by band.** The number is secondary, so avoid implying "73 beats 71".
- **Deterministic ties:** score, then momentum, then role name A–Z.
- **Empty or near-empty profile** (fewer than 3 skills after pre-fill): don't show a misleading ranking. Show "starter roles" with an explanation: *"Add a few skills or tasks to get a personalised ranking."*
- **No double counting:** momentum affects the score once (as a component). Gap ordering uses score gain per hour (§6), which already reflects momentum, so don't add another momentum multiplier.

### 5.6 Explanations (templates, not LLM)
Generate 2–3 reasons per role from `components` and `matchedSkills`. Examples:
- Skill: *"You already have {n} of {m} core skills ({list})."*
- Momentum: *"{skills} are **Rising** in tech hiring (source date {data_as_of})."* / *"{skill} is **Cooling**."*
- Direction: *"A nearby move from {current family}: it uses what you already know."*
- Feasibility: *"Closing the gap needs ~{h} h, which fits your {timeframe} plan at {w} h/week."* / *"…needs ~{h} h, more than your plan allows ({available} h). Consider a longer timeframe."*
- An LLM may optionally rephrase the final sentences for readability. It must receive only the computed reasons, never user free text, and must not change numbers. Fall back to the raw templates if it fails.

### 5.7 "How this score was calculated" panel
An expandable panel on each role card shows:
- the four components with their values and the weights used
- the matched skills (user level vs required level) and missing skills
- trend source and `data_as_of` from the snapshot
- flags (e.g. education note)

This is both the explainability feature for judges and the team's debugging tool.

---

## 6. Skills gap (the main product)

For the selected role (or each of the top 3):

```ts
GapItem = {
  skillId, name,
  currentLevel, requiredLevel,
  type: "learn" | "improve",      // learn = level 0, improve = below required
  hours,                          // from learn_hours, scaled to the level difference
  momentumLabel,                  // Rising / Stable / Cooling / No data
  isCore: boolean,
  scoreGainPerHour,               // see below
  fitsTimeframe: boolean          // cumulative hours in order <= availableHours
}
```

- **Ordering:** core skills first, then by `scoreGainPerHour` descending.
  `scoreGainPerHour = (score with this skill at requiredLevel − current score) / hours`, computed by re-running the pure scoring function. This is cheap.
- **Cumulative fit:** walk the ordered list and mark items as fitting the timeframe until the available hours run out. Show a clear line: *"Fits in your 3-month plan"* / *"Beyond your current plan"*.
- **Copy:** "Learn SQL" for missing skills, "Strengthen SQL" for improve items.
- The gap list (in order) is the input to the existing pathway generator, which also applies AI comfort and preferred format.

---

## 7. Optional: "What-if" simulator (only after everything else passes)

- On the results screen, show the missing skills as toggles: *"Pretend I learned Python"*.
- Toggling re-runs `rankRoles` client-side and animates the score and band changes (e.g. *Finance Automation Specialist 58 → 76*).
- Highlight the **"next best skill"**: the gap item with the highest `scoreGainPerHour` across the top roles.
- No new logic. It reuses the pure function.

---

## 8. Persona tests (write these BEFORE tuning weights)

Create `tests/personas/` with 5 fixtures. Each has a full questionnaire answer set and **expectations written by the team** (a "career counsellor" view). Assert **top-3 membership and band**, not exact order or exact scores.

| # | Persona | Key answers | Expected (team to confirm) |
|---|---|---|---|
| 1 | Reconciliation Associate, 10+ yrs | Finance, Excel + ERP, tasks: reconcile, monthly reports, macros; direction Nearby; 6 months; 3 h/week | Top 3 includes Finance Data Analyst, Finance Automation Specialist, FP&A Analyst |
| 2 | Same as #1 but direction **Grow** | — | Top 3 stays in finance-related families; includes AI-enabled Accountant / Controller |
| 3 | Fresh graduate, <2 yrs | Python + SQL, few tasks; direction Switch | Data Analyst / ML-adjacent roles rank above finance roles |
| 4 | "None of these" tools, no tasks, role with sparse pre-fill | — | Empty-profile path: starter roles + prompt to add skills, no misleading ranking |
| 5 | Strong data profile, 12 months, 8 h/week | SQL, Python, BI confident | Data Engineer / BI Developer reach "Strong"; feasibility ≈ 1 |

Also unit test:
- each component formula with small hand-calculated cases
- the core coverage cap
- tie-breaking
- the gap ordering and cumulative `fitsTimeframe`
- the skill ID validation (§2)

Tune weights in `config/scoring.yaml` **only** until the persona tests pass. If a persona expectation seems wrong, flag it for the team rather than bending the formula.

---

## 9. Results UI

- **Role cards** (top 3–5): name, band badge, score, a component breakdown bar, 2–3 reasons, flags, the "How this score was calculated" panel, and a "See my skills gap" button.
- **Gap view:** an ordered list with learn/strengthen label, hours, momentum badge, core marker, and a timeframe-fit divider.
- **Provenance:** wherever momentum is shown, include the trend source and data date (reuse the provenance component from the AI signal phase).
- Phone width (~380px): cards stack; the breakdown bar stays readable.
- Use the existing chart and UI libraries.

---

## 10. Build order

1. Repo inspection summary.
2. Apply the amendments to the AI signal feature (§1).
3. Extend `skills.yaml` and add the skill ID validation test (§2).
4. Questionnaire changes: role pre-fill, tasks, levels, field usage and badges (§3), plus the UI fixes (§4).
5. Role catalogue and families config (§5.1). List any TODO source codes.
6. Persona fixtures with team expectations (§8). Tests should fail at this point.
7. Pure scoring function, guards and explanations (§5.2–5.6), then tune until the persona tests pass.
8. Gap computation (§6) and its tests.
9. Results UI, the score-calculation panel and the gap view (§5.7, §9).
10. Hook the gap list into the pathway generator.
11. Optional: what-if simulator (§7).

Run the tests after each step and give a short summary before moving on.

---

## 11. Acceptance criteria

- [ ] No CV upload or parsing anywhere. All profile data comes from the questionnaire.
- [ ] Every skill ID in roles, tasks, tools and pre-fill exists in `skills.yaml` (test passes).
- [ ] Every questionnaire badge and helper text truthfully states whether the field affects the ranking, the pathway, or nothing.
- [ ] The AI comfort slider label and handle always agree; the default timeframe is a visible option.
- [ ] `rankRoles` is pure and deterministic, with all weights and thresholds in config.
- [ ] All 5 persona tests and all unit tests pass.
- [ ] Every role card shows band, score, breakdown, reasons, and the calculation panel with the trend source date.
- [ ] The gap list is ordered, has hours, and marks what fits the user's timeframe.
- [ ] An empty profile shows starter roles, not a misleading ranking.
- [ ] No user data (including free text) is sent to any external API or the AI companion.
- [ ] No invented O\*NET / ESCO codes. Unverified codes are marked TODO.

---

## 12. Out of scope (for now)

- CV upload and parsing.
- ML / embedding-based matching or learned weights.
- Using years of experience or education in the score itself.
- arXiv research layer (still deferred from the AI signal phase).
