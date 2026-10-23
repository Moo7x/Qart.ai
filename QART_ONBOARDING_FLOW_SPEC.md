# Qart.ai — "Find my path" onboarding flow and app shell

> Build spec for Claude Code. Read after `AI_SIGNAL_SPEC.md`, `QART_NEXT_STEPS.md` and `QART_LEARNING_PLAN_SPEC.md`.
> Visual reference: the "Find my path flow" artboard on the Qart.ai Onboarding design canvas (landing → 3 question steps → matching → tabbed app).

## 0. Before writing code

1. Explore the repo. Find the existing questionnaire page/component, the role-ranking code, the Future Skills Radar page and the learning-plan page.
2. Propose a short plan (files to add, files to change, routes) and wait for approval before editing.
3. **Reuse, don't duplicate.** The questions already exist. This spec re-arranges them into steps; it does not create a second questionnaire.

## 1. What changes for the user

Today the questionnaire is one long page. The new flow is:

1. **Landing** — one big **Find my path** button in the centre. A small secondary link, **Look around first**, opens the app without answering anything.
2. **Questions** — the existing questions split into 3 steps, one screen each, with **Next** and **Back**. Step 3's button reads **Find pathway**.
3. **Matching** — a "We are looking for the best match" screen with 5 stage cards that tick from *Waiting* → *In progress* → *Complete* as the backend actually works. Then **See my matches**.
4. **App** — 4 tabs: **Find my path · Future skills · Get matched · Generate pathway**.
   - **Get matched** and **Generate pathway** are locked until the questions are submitted.
   - **Future skills** is always open (it shows market data, not personal data).

## 2. Routes

Adapt names to the existing router; keep the shape.

| Route | Screen |
|---|---|
| `/` | Landing |
| `/onboarding/1`, `/onboarding/2`, `/onboarding/3` | Question steps |
| `/matching` | Matching progress |
| `/app/path` | Tab: Find my path (answer summary, edit) |
| `/app/skills` | Tab: Future skills → existing radar page |
| `/app/match` | Tab: Get matched → existing ranking page |
| `/app/pathway` | Tab: Generate pathway → existing learning-plan page |

Steps are URLs so the browser Back button works and a refresh keeps the user's place.

## 3. State

- **One onboarding answers object** is the single source of truth, the same object the ranking code already reads. Shape stays as it is now; only the UI around it changes.
- Persist it on every change (to `localStorage` for the demo, and the backend if one exists), so leaving mid-way and coming back restores answers.
- `profileComplete: boolean` is set **only** when Step 3 is submitted *and* matching finishes successfully.
- Editing answers later (from the Find my path tab) re-runs matching and re-ranks roles. Keep `profileComplete = true` during the edit, so tabs don't re-lock.

## 4. The three steps

Move the existing fields into these groups (titles are user-facing copy):

**Step 1 — Where you are now**
- Name (optional)
- Current role (**required**; keep the role pre-fill of skills from `QART_NEXT_STEPS.md`)
- Industry
- Highest education
- Years of experience (**required**)
- Tools you use today
- Weekly tasks, if that question exists

**Step 2 — What you enjoy and where you're heading**
- What do you enjoy?
- Where do you want to go next? (**required**: grow / nearby role / switch)
- Timeframe

**Step 3 — How you learn**
- Weekly learning hours
- AI comfort (0–10)
- Preferred format
- Anything else (optional)

Rules:
- A progress bar shows "Step N of 3".
- **Next** is disabled until that step's required fields are filled. Next to it, say exactly what's missing, e.g. "Add your current role and years of experience to continue."
- Required fields are marked with `*`.
- **Back** on Step 1 returns to Landing without clearing answers.

## 5. Matching screen

Five stages, each tied to a **real** call or function. No fake timers.

| # | Title | Sub-line | Backed by |
|---|---|---|---|
| 1 | Reading your answers | Turning your three sections into a skills profile | validate + save answers |
| 2 | Mapping your skills | Matching what you do to standard skill IDs | answers → canonical skill IDs |
| 3 | Scanning the job market | Checking demand trends from public job postings | load radar signals (`AI_SIGNAL_SPEC.md`) |
| 4 | Ranking future roles | Scoring each role on skills, interests, demand and time | ranking (`QART_NEXT_STEPS.md`) |
| 5 | Building your skills gap | Listing what you have and what to learn next | gap per top role |

Behaviour:
- Run the stages in order. Show a stage *In progress* while its promise is pending and *Complete* when it resolves.
- Give each stage a **minimum display time of ~400 ms** so fast local calls still read as steps. Add no artificial delay beyond that.
- The heading switches from "We are looking for the best match" to "Your matches are ready". Then show **See my matches** → `/app/match`.
- **On error:** mark the failed stage red, explain it in one line, and offer **Try again** (re-run from the failed stage) and **Back to questions**. Never show partial matches as final.
- Put the stage list in `aria-live="polite"` so screen readers hear progress.

## 6. App shell and tab gating

- The tab bar sits under the logo on every `/app/*` route. The current tab is highlighted.
- **Locked tabs** (Get matched, Generate pathway when `profileComplete` is false):
  - Show a lock icon and a dashed, muted style.
  - Stay clickable. Clicking opens a panel: "*Get matched* unlocks after Find my path", one line on why, and an **Answer the questions** button → `/onboarding/1`.
- **Guard the routes, not just the buttons.** Opening `/app/match` or `/app/pathway` by URL without a complete profile shows the same locked panel. It must not show empty or broken results.
- **Find my path tab:** three rows, one per step, in the "Complete" row style (green check, title, one-line summary of the answers, "Complete" on the right). Before submission they show a dashed circle and "Not started", with **Start questions**. After submission the button reads **Edit answers**.
- **Future skills / Get matched / Generate pathway:** render the **existing** pages inside the shell. Do not rebuild them.

## 7. Look

Use the tokens already in the app. If none exist, use the prototype's:
- Background `#F5F4F1`, cards `#FFFFFF`, border `#E2DFD9`, radius 16–20 px
- Text `#1F1E1C`, muted `#5F5C57`; accent `#2B66D1` (hover `#1E4FA8`)
- Success `#166534` on `#E7F4EA`
- Fonts: Inter for UI, Source Serif 4 for intro lines

Accessibility:
- Touch targets ≥ 44 px.
- Real `<button>` and `<a>` elements; chips use `aria-pressed`.
- Visible focus rings.
- Spinner respects `prefers-reduced-motion`.
- Works at phone width: tabs wrap to 2×2, cards go full width.

## 8. Done when

- [ ] Landing → 3 steps → matching → `/app/match` works end to end with a demo persona.
- [ ] Next is blocked until required fields are filled; the hint names the missing fields.
- [ ] Refreshing on any step keeps answers and position.
- [ ] Matching stages are driven by real calls. Forcing an error in stage 4 shows the error state, and Try again recovers.
- [ ] Without a complete profile, `/app/match` and `/app/pathway` (by click *and* by URL) show the locked panel.
- [ ] "Look around first" opens Future skills with the other two tabs locked.
- [ ] Editing answers re-ranks roles, and the new top role appears in Get matched.
- [ ] Existing radar, ranking and learning-plan features behave exactly as before.
- [ ] No console errors. Usable at 390 px width.

## 9. Out of scope

- CV upload (dropped on purpose).
- Accounts / login.
- Changing the scoring formula or the radar's data sources.
