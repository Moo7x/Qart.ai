# Onboarding questionnaire and held skills (`src/engine/questionnaire.py`)

## 1. What it does
Turns the onboarding answers into the person's skills, each with a level: **Heard of it** (0.3), **Use sometimes** (0.7) or **Confident** (1.0).

## 2. Why it exists
There is no CV upload. The role ranking and the skills gap (QART_NEXT_STEPS §5–6) need to know which skills a person has and how well, in the app's one skill vocabulary.

## 3. How it works
- **Current role** pre-ticks that role's typical skills.
- **"Which of these do you do most weeks?"** adds each task's skills.
- **Tool chips** add their skills. "None of these" clears the other chips, and the other chips clear it.
- Everything added starts at **Use sometimes**, and adding never lowers a level the person already set.
- The person taps a chip to change its level, or removes it. The final chips are saved as `preferences.skill_levels`.
- **Held skills** are those levels, raised by practice evidence. A skill shown in a case with help counts at least as "use sometimes"; shown on your own, "confident". A claim alone adds nothing.

## 4. Where in the code
- Config: `catalogue/questionnaire.json` (current roles, tasks, tools, levels)
- Logic: `src/engine/questionnaire.py` (`prefill_levels`, `held_skills`)
- Endpoints: `GET /api/questionnaire`, `GET /api/held-skills/{id}`, and the checks in `POST /api/profile`
- UI: `web/src/pages/Intake.tsx`
- Tests: `tests/test_questionnaire.py`, `tests/test_skill_vocabulary.py`

## 5. Example
Reconciliation Associate who ticks "Record or edit Excel macros" and the Python chip:
- The chips become Excel modelling, reconcile to source, ERP, duplicate detection, financial reporting, Excel automation and Python, all at "use sometimes".
- She raises Excel to "confident" and removes ERP.
- After a practice case where she catches a cut-off error on her own, cut-off timing joins her skills as "confident".

## 6. Limits
- Levels are self-rated, and the values 0.3, 0.7 and 1.0 are declared choices, not data.
- Mappings from roles and tasks to skills are team curation.

## 7. Questions and answers
- *Why not ask a level for every skill?* It would be a long grid. Chips with tap-to-change keep the form short (§3.5).
- *Can evidence lower my level?* No. Missing a case is practice, not proof you lack the skill.
