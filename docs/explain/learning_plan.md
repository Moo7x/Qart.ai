# Learning plan (`src/engine/learning_plan.py`)

## 1. What it does
It turns the ordered skills gap of the role you chose into a week-by-week plan of real courses and short hands-on milestones. For each step it gives hours, weeks, cost to you, a source link and the date the course was last checked.

## 2. Why it exists
Domain 1 must-have 4: "an ordered learning plan with estimated time, using free or low-cost resources (online courses, HRD Corp-claimable programmes)". The gap decides *what* to learn and in which order. The plan decides *how* (which course), *when* (which weeks) and *at what cost*.

## 3. How it works
One pure function, `build_learning_plan`: no network, no AI model, no randomness. All values are in `catalogue/plan.json`.

1. **Cost to you:**
   - free → RM0;
   - free-if-eligible → RM0, with a note on who is eligible;
   - HRD-claimable → RM0 only if you are employed and your employer is HRD Corp-registered. The wording says "if approved" and that HR applies via e-TRiS before the course starts. If you're not sure, you see the listed price and "ask your HR";
   - otherwise the listed price;
   - no stated price → unknown, never counted as free.
2. **Filters:**
   - a course is dropped only when a *known* answer breaks its limits (for example age 31–45 for an 18–30 programme). "Prefer not to say" keeps it, with a note;
   - your budget: free only, up to RM200, or employer pays;
   - and the course must start near your level (at most 0.3 above it).
3. **Choice:**
   - up to 2 courses per skill, and a single course that covers the whole step wins;
   - a declared score: free +3, RM50 or less +1.5, your format +2, a certificate if you want one +1, your language +1, self-paced +0.5, shorter up to +1;
   - ties break on cost, then hours, then id;
   - the next 2 courses are kept for "Swap";
   - a course over 3× the gap's estimated hours is used only when nothing shorter exists.
   - **employer-funded first:** for someone employed who chose "Any, if my employer pays" and whose employer is HRD-registered (or who is not sure), an HRD-claimable course gets +5, so it wins even at its listed price. If they're not sure, the action item first asks HR whether the company is registered.
4. **Order:**
   - with AI comfort 3/10 or below, an AI-literacy course goes first. AI untuk Rakyat is chosen only if you're known to be eligible (18–30 and Malaysian); otherwise you get a course open to everyone;
   - after that, the gap order (core first, then score gain per hour), moved so a skill never comes before its prerequisite.
5. **Schedule:**
   - hours × 1.2 (practice buffer), packed into weeks at your weekly hours;
   - a milestone after each core skill and at least every 4 weeks, never two in a row;
   - steps past your timeframe go into a "Next phase", never cut;
   - a skill with no course still appears, with its estimated hours.

## 4. Where in the code
- `src/engine/learning_plan.py`
- `catalogue/plan.json`
- `catalogue/courses.json` and `catalogue/milestones.json` (see resources.md)
- `tests/test_learning_plan.py`: every cost-table row, eligibility, each budget option, level coverage, single-course preference and chaining, the overshoot rule, scoring and tie-breaks, prerequisite order, AI-literacy-first at 3 and 4 and the AI untuk Rakyat switch, week packing, milestones, the next phase, gaps without courses, HRD action items, determinism.

## 5. Example
Persona p1 is a Reconciliation Associate aiming for Finance Data Analyst. She has 3 h/week for 6 months, AI comfort 2, an HRD-registered employer, and chose "employer pays". With the draft courses included, her plan is:
1. a 30-minute free generative-AI intro first;
2. a 2-day HRD-claimable AI data analytics workshop covering SQL and Python (RM0 to her, with an action item to ask HR to apply via e-TRiS);
3. a SQL-and-dashboard milestone;
4. a free variance-analysis course;
5. Stanford's statistics course (free for eligible Malaysians through Rakyat Digital).

That is 41 h in 14 weeks, inside her 26.

## 6. Limits
- The plan uses only verified courses unless `SHOW_DRAFT_RESOURCES=true`. Until the team reviews the drafts, many skills show "no matching course yet".
- Many courses are short, so notes say when the catalogue stops short of the level needed.
