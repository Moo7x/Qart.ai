# Qart.ai · Person B: App, Cases & Companion (the "experience")

*You own: the web app (Employee / HR / Senior views), the finance cases, the companion agent (stepped help, tools, grader), voice, Replit deployment, deck and video. Suggested for the team member who prefers front end and agent building.*
*Read first: `PROJECT_PLAN.md` and `team/00_SHARED_CONTRACT.md`. All times MYT.*

**You don't need the engine.** Until merge point **M1**, work from **mock JSON** (`schemas/examples/`) that follows the contract.

## Your increments (build the base first; every increment deployed and committed)
| Increment | Your part | Target | If it slips |
|---|---|---|---|
| **0 Base** | App shell deployed on Replit · Intake · Workspace + text companion (stepped help) on **one case** (case_003) **with basic UI actions** (pop-in, highlight, open document, show check, trace; Task B4b) · Result → Event · My skills · My future (mock data until M1) | Thu midday | Plain HTML tables are fine; styling later |
| **1 Golden journey** | case_006 + checkin_001 (+ checkin_002 optional) · targeted next case from A · "1 of 2 independent successes" wording · revised path view | M1, Thu 21:00 | Fewer screens; keep the journey |
| **2 Evidence → recompute** | Assumptions panel (HR, synthetic): signal diff → suggested review → approve → updated requirement card and ranking | Fri midday | A single "review & approve" card is enough |
| **3 Trust checks** | case_001 (clean) + case_007 (AI false alarm) in the journey · **acceptance cases** authored for A (below) | Fri afternoon | At least 1 clean case + 1 false-alarm case |
| **S2 Voice spike (2 h)** | Browser speech with interruption, against the pass tests below | Fri | **Drop for the preliminary** and keep text; note it in the decision log |
| 4 Polish | Senior console (if A's gate spike passed) · HR summary · sources page · demo mode | Fri evening | Whatever fits |

Drop rule: when a timebox ends without passing its test, stop, write one line in `docs/decision_log.md`, tell A, and move to the next increment.

---

## 0. Before you start (Day-0 session with A, Wed 21 Oct)
- [ ] Agree on the contract and commit `schemas/examples/*.json`
- [ ] Branch `b/app`. Create the **Replit project** (import from GitHub) and deploy a hello-world **today**, so you have the URL early
- [ ] Get the LLM key into Replit Secrets and your local `.env`
- [ ] Find 1 finance/accounting student or staff member who can review your cases for 20 minutes (Thu)

---

## 1. Phase 1 (Wed 21 evening → Thu 22): app, cases, companion

### Task B1: Web app shell *(~3 h)*: `web/` (React + TypeScript + Vite)
- Routing, a role switcher on the landing page (**Employee: Aina / Siti · HR: Nadia · Senior: Mr Lim**, all synthetic), and a "Synthetic demo data" badge.
- A UI kit for speed (e.g. shadcn/ui or MUI) and Recharts for small charts. Mobile-friendly Employee view.
- `web/src/api.ts` with a `USE_MOCKS` flag. Mocks read `schemas/examples/*.json`, so swapping to A's endpoints at M1 is one switch.
- FastAPI serves `web/dist` (shared `src/main.py`). Update `.replit` so Run builds the web app and starts uvicorn.

### Task B2: Screens *(~5 h)*
| Screen | Shows | Data |
|---|---|---|
| **Intake** | Role, skills + self-rated confidence sliders, interests, weekly hours | `POST /api/profile` |
| **Work queue** | Cases (practice / real / check-in), status | `GET /api/cases` |
| **Workspace** | Ledger table, bank table, documents panel, the **AI's claim and proposed adjustments**, rows highlighted by the companion | `GET /api/cases/{id}` |
| **Companion panel** | Chat, an **"I'm stuck" button** (raises the help level one step), help-level indicator, decision buttons **Sign off / Correct / Escalate** (+ which rows) | B's companion routes |
| **Result** | Correct or not, what was missed, skills updated | grader + `POST /api/events` |
| **My skills** | Each skill's state (self-reported / observed with help / demonstrated independently *on these cases* / insufficient), the **"why" sentence** and the **evidence trail** (which cases, which help level), a **reality gauge** (self-rating next to the evidence state). **No percentages.** A "this case was unfair / the companion was wrong" flag button | `GET /api/skills/{user}`, `POST /api/events/{id}/flag` |
| **My future** | Snapshot card (**source + date**, labelled "historical data replay" when replaying), **scenario toggle**, ranked roles with **score-breakdown bars** + formula, gap list, **requirement card** (tasks → who does them under this scenario → weights → why: assumption + evidence), **path timeline** (hours, sources, SDG chips), "choose this path". Every number is badged *evidence*, *assumption* or *synthetic* | A's endpoints |
| **HR summary** | **Aggregates only**: skill states by count across the team (groups <5 hidden), training demand per scenario, and the **assumptions panel** (layer B: task allocation per scenario, suggested reviews from new snapshots, accept → new version). **No names, no "who should move where".** Note: *"Individual recommendations are visible only to each employee."* | `GET /api/hr/summary`, `GET/PUT /api/assumptions` |
| **Senior console** | Sampled sessions, **optimiser proposals** (scope = playbook, diff, optimisation-set and acceptance-set counts before→after, regressions, rollback), Approve / Reject, version history | A's optimiser endpoints |
| **Sources & data** | Every dataset/model with licence and date, plus "synthetic data" and privacy notes | static |

**v2 priority = the golden journey** (contract §6): Intake → Workspace + Companion + Result (case_003 miss → stepped help) → targeted case → check-in → My skills (state + why + trail) → My future (revised path + requirement card). Senior console, HR summary and Sources can be stubs until Phase 2, **except the assumptions panel, which golden-journey step 6 needs by M2**.

### Task B3: Cases *(~4 h)*: `cases/*.json` (contract "Case" format)
A synthetic company (e.g. **Kopi Kita Sdn Bhd**, a café chain; amounts in MYR) and its **October bank reconciliation**:
| id | Mode | What's going on | Skills | Correct decision |
|---|---|---|---|---|
| case_001 | practice | **Clean**: timing items (deposit in transit) properly documented | cutoff_timing, escalation_judgment | sign_off |
| case_002 | practice | Duplicate supplier payment recorded twice | duplicate_detection, recon_to_source | correct |
| case_003 | practice | 1,520 keyed instead of 1,250; AI hides it as a "rounding" adjustment | transposition_check, unsupported_adjustment, ai_output_review | correct |
| case_004 | practice | November deposit counted in October (cut-off) | cutoff_timing | correct |
| case_005 | practice | USD invoice converted at the wrong rate | fx_conversion, recon_to_source | correct |
| case_006 | practice | Large manual adjustment with **no document** | unsupported_adjustment, escalation_judgment | escalate |
| case_007 | practice | **AI false alarm**: AI says it doesn't reconcile, but it does once a bank fee is matched | ai_output_review, recon_to_source | sign_off |
| case_008 | practice, `agentic` variant | AI prepared the whole month-end pack; one schedule has an error | ai_output_review, escalation_judgment | correct |
| checkin_001/002 | checkin | Fresh variants of 003 and 006, **no help** | as above | as above |
| real_001/002 | real | Same structure, presented as "today's work" | — | — |
- Keep each case small (8–15 rows) so the demo is readable. Every number must add up exactly, so check with a spreadsheet.
- **Include plausible alternative explanations** (e.g. a difference that *looks* like an error but is a legitimate timing item) and **clean cases**. These test that neither the companion nor the learner "flags everything".
- Record each case's difficulty (1–3) and which skills it can evidence.
- **Acceptance cases (for A's evaluation, Increment 3):** write **6 extra cases with different reasoning patterns** from the practice cases. Use different error mechanisms *and* different structures, e.g.:
  - a split payment
  - a bank-side error rather than a ledger error
  - a reversed entry
  - two offsetting errors
  - a legitimate unusual item that looks wrong
  - an FX case with a partial payment
  
  Plus **2–4 more kept completely aside** as the final untouched set. Hand them to A for `eval/acceptance/`. **Don't reuse them as practice cases, and don't show them to the optimiser.**
- Get your finance reviewer to sanity-check them on Thu. Note who reviewed and when in `docs/decision_log.md` (no personal data).
- A will generate variants from these for evaluation, so **keep the format strict**.

### Task B4: Companion agent *(~6 h)*: `src/companion/`
**Design rule: deterministic code controls *what* the companion may reveal; the LLM only writes *how* it says it.**
- **Tools** (Python functions the LLM can call through function calling):
  - `get_section(case, "ledger"|"bank"|"documents"|"ai_output")`
  - `recompute_totals(case)`
  - `match_entries(case, tolerance)`
  - `find_document(case, doc_ref)`
  - `compare_amounts(a, b)`
  - `list_adjustments(case)`
- **Help ladder (state machine):**
  - Level 0: user tries alone; the companion only answers clarifying questions.
  - "I'm stuck" → 1 question ("What would make this total change?") → 2 hint ("Look at the adjustments") → 3 explanation (the concept) → 4 answer (the specific rows).
  - Record `help_level_max` and `help_steps`. In **check-in** mode the ladder is disabled.
- **Playbook:** `playbooks/playbook_v1.md` is the checking procedure the companion follows (e.g. "1. recompute both sides; 2. match every ledger line to bank or document; 3. challenge every manual adjustment…"). It's loaded into the system prompt. **A's optimiser proposes `playbook_v2`.** Keep it short and editable.
- **Guardrails:**
  - The companion never sees `ground_truth`.
  - A validator checks that every row ID or amount it mentions exists in the case. Otherwise regenerate.
  - It never claims certainty it doesn't have.
- **Decision → Event:** `grader.grade()` (the only code that reads ground truth) computes correctness and `skills_evidence` (each skill: success or fail at the help level used). It also records `difficulty` and `session_id`.
  - **In practice mode, a wrong sign-off isn't the end.** The grader reveals that something was missed, and the companion then walks the learner back through the ladder. The event records "missed, then found at help level N". This is golden-journey step 2.
  - Provide a **"companion was wrong / case unclear"** flag. Flagged events don't count toward skills (contract).
  - **Wording rule in the UI:** say "evidence" ("you caught this after a hint"), never "your skill is X%".
  - `issue_found_by` = `user` if flagged before level 3, otherwise `companion`.
  - Build the `Event` (contract) and send it to `POST /api/events` (mock until M1).
- **`auto.py: auto_diagnose(case, playbook_path)`:** the same agent and tools with no user, returning the diagnosis. **A's evaluation and optimiser depend on this, so deliver it by C1.**
- Voice comes later. Keep the companion's messages short (1–3 sentences) so they work spoken.

### Task B4b: The agent drives the UI (the "wow" piece) *(base: ~3 h; extras later)*
The companion acts **inside our own app**, not on the real computer, so it's reliable. Some of its tools are **UI actions**: the backend returns `ui_actions` (contract §5) and the front end animates them.
| UI action | What the user sees | When |
|---|---|---|
| `pop_in` | The companion slides in: *"Want a second look before you sign off?"* | When the AI card claims "reconciles", or the user hovers over Sign off |
| `highlight_rows(rows)` | Rows glow. Optionally a connector line between the matching ledger and bank rows (e.g. RM1,520 ↔ RM1,250) | Hint level and above |
| `open_document(doc_ref)` | The invoice/receipt panel slides open with the key amount circled | Hint level and above |
| `show_check(check, result)` | A small animated "check" panel: *"Recalculating… ledger RM48,270 vs bank RM48,000 → RM270 unexplained"* | Whenever the agent runs a tool |
| `move_cursor_to(element)` | An agent cursor/avatar glides to the element and pulses | Extra (later) |
| live **trace strip** | Step list: *checking totals → matching rows → reading invoice* | Always (base) |
- **Rules:**
  - The help ladder still limits what the agent may reveal. Before hint level it only shows *where to look* (e.g. totals), **never the answer rows**.
  - **The user still decides.** The agent never clicks Sign off / Correct / Escalate itself.
  - Every row/doc it points to must exist in the case (the validator applies).
- **Base:** pop-in + highlight + open document + show_check + trace strip, on case_003.
- **Extras if time allows:** cursor glide, connector lines, smooth scrolling, sound on voice.
- Implementation tip: a small `uiActionQueue` in React that plays actions in order (300–600 ms each). It must be cancellable when the user interrupts or types.

**C1 checkpoint (Thu ~14:00):** show A a real `Event` JSON from a played case. Confirm `auto_diagnose()` runs on case_003. Confirm A's recommendation JSON renders in "My future" (from A's output, even pasted as a mock).

### ⛔ Stop and merge, M1 (Thu ~21:00)
Stop feature work when:
- (a) it's 21:00, **or**
- (b) a full case can be played end to end and emits a valid `Event`, **or**
- (c) you're blocked >1 h on something needing A.

Then merge `b/app` → `main`, switch `USE_MOCKS` off, and run the **golden journey test, steps 1–5** (contract §6) **on the Replit deployment URL**. **Don't start the spikes until it passes.** Steps 6–7 by M2.

---

## 2. Phase 2 (Fri 23): voice, HR, senior, polish

### Task B5: Voice with interruption: **timeboxed spike, 2 h, droppable**
- The time estimate is **untested**. Browser speech recognition has **compatibility limits**: it isn't available in every browser (check MDN's SpeechRecognition compatibility table), may depend on a remote recognition service, and needs microphone permission. Target Chrome/Edge for the demo.
- **Pass tests (all four, or drop voice for the preliminary):**
  1. When the user starts speaking, playback stops within about 0.5 s.
  2. The **stale companion response is cancelled**: pending text, queued speech, and any pending tool action or request (abort it), not just muted.
  3. The interruption is transcribed and **answered in the context** of the highlighted rows.
  4. Text chat keeps working throughout and after.
- **Fastest route:** the browser **Web Speech API** (SpeechRecognition + speechSynthesis).
  - Barge-in: on the recognition `speechstart`/`onresult` event, call `speechSynthesis.cancel()`, abort the in-flight request (AbortController), and discard queued output.
  - Test BM (`ms-MY`) later.
- **Higher-quality route** (if time and keys allow): a realtime speech API over WebRTC with an ephemeral token from the backend. It has documented interruption handling. Interrupting must also **cancel any pending companion action**, not just the audio.
- Text always stays available. Declare whichever you use.

### Task B6: HR summary + Senior console *(~3 h)*
- HR summary: aggregate counts from `/api/hr/summary` (groups <5 hidden), training demand per scenario, the assumptions panel. A note: *"Individual recommendations are visible only to each employee. The system never makes promotion or dismissal decisions."*
- Senior: list `OptimizerProposal`s and show `editable_scope: playbook`, the diff, the **acceptance-set** counts before→after (plus false alarms on clean cases and invalid citations), and regressions. Approve / Reject calls A's endpoint. Show the version history and the **rollback** button. **Include only if the cycle works reliably** (Should item); otherwise show a recorded run labelled as such.

### Task B7: Polish for judges *(~2 h)*
- Loading states, empty states, error messages, a **"Demo mode"** toggle that uses cached LLM replies for the demo personas (labelled), the Sources & data page, and the mobile layout for the Employee view.
- Run the demo script (`PROJECT_PLAN.md` §8) twice and fix what's awkward.

**C2 (Fri ~14:00):** agree what's cut. **M2 (Fri ~22:00):** full rehearsal with A, then **feature freeze**.

---

## 3. Sat 24: submission (your parts)
- [ ] **Pitch deck:** problem → user and moment → demo screenshots → how it works → differentiation → evidence and KPIs → SDG 4.4 impact → team. Consistent product name everywhere.
- [ ] **Video (5–7 min, hard cap 7:00; −1 pt per 30 s over):** record with OBS or Loom at 1080p, voice-over following the demo script, captions if possible. Upload to YouTube (Unlisted is fine if the link works logged out; test it in an incognito window).
- [ ] PRD non-technical sections: 2.1 problem (≤250 words), 2.2 solution (≤300), 3.2 design thinking (≤200: who you spoke to, what changed because of it)
- [ ] **Replit proof:** deployment URL + project history screenshot → `submission/`
- [ ] Check that the live URL works in incognito on a phone and a laptop. **Don't redeploy after the deadline.**

---

## 4. Guidance for your coding agent (Claude Code / Codex)
**Start every session with:**
> "Read AGENTS.md, PROJECT_PLAN.md and team/00_SHARED_CONTRACT.md. You are helping Person B, who owns web/, cases/, src/companion/, src/api_companion.py. Don't edit other folders. Follow the JSON contract exactly. The companion must never read ground_truth (only grader.py does), and must never mention rows or amounts that don't exist in the case."

**Good task prompts (one per session, small):**
1. "Scaffold web/ with Vite + React + TypeScript, a role switcher, routes for the screens in team/PERSON_B_APP_AND_COMPANION.md Task B2, and api.ts with a USE_MOCKS flag reading schemas/examples."
2. "Build the Workspace screen: ledger table, bank table, documents panel, AI claim card, and row highlighting driven by a `highlights` array."
3. "Implement src/companion tools (Task B4) as pure Python functions with unit tests on cases/case_003.json."
4. "Implement the help-ladder state machine and the companion loop with function calling; load playbooks/playbook_v1.md; validate that every row ID in the reply exists."
5. "Implement grader.grade() and the Event builder exactly per the contract, and auto_diagnose() for evaluation."
6. "Add Web Speech API voice with barge-in (cancel speech on user speech start), keeping text chat."

**Review rules for yourself:**
- Read every diff. You must be able to explain the companion's logic and the help ladder to a judge.
- Never let the agent invent finance facts. You verify every case's numbers in a spreadsheet.
- Log each library, API and model in `docs/DECLARATION_LOG.md` as it's added.
- Commit small and often on `b/app`.

## 5. Things that will bite you (and how to avoid them)
- **LLM latency in the live demo:** demo mode with cached replies (labelled), plus short messages.
- **The companion "solves" the case too early:** the ladder is enforced in code, not in the prompt alone.
- **Hallucinated rows or amounts:** the validator plus tools-first checking.
- **Replit build issues:** deploy on day 1 and keep deploying daily. Don't leave the first deployment for Saturday.
- **Privacy optics:** the UI wording says the employee owns their record, HR sees aggregates, and the data is synthetic.
- **Explainability:** at M1 and M2, give A a 15-minute walkthrough of the companion and UI. Judges can ask either of you about any part.
