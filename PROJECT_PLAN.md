# Project Plan v2: SDC Hackathon 2026, Domain 1 (Aiversecity Future-Ready Workforce)

*Product name: **Qart.ai** · v2.2, 21 Oct 2026 · Team of 2*
*Tagline: **"Your mistakes are your future skills, once you learn how to handle them."***

> **v2.1 (21 Oct):**
> - The golden journey now matches the evidence rules: one check-in = "1 of 2 independent successes", and the path keeps a confirmation step.
> - Updated external evidence is shown as ingestion → review → approval → recompute.
> - Voice is a timeboxed spike with pass criteria.
> - Acceptance cases are independent reasoning patterns, never tuned against.
> - Qualified wording for FinBalance and HR suppression.
> - **Build strategy:** a deployed base first, then shippable increments, with drop rules (§9).
>
> **What changed in v2 (summary):**
> - **Same idea, same features, more precise.** The future-role logic now separates three kinds of input (external evidence · company adoption assumptions · employee evidence).
> - **Skill wording is honest.** Help level is *evidence*, not a measurement; parameters are provisional.
> - **The self-improvement loop has a hard boundary** (it edits the playbook only).
> - **The HR view is aggregate-only.**
> - **Novelty claims are replaced** by advantages we can demonstrate.
> - **The evidence is finance-first.**
> - **The build is re-prioritised** around one "golden journey".
> - **Factual fixes:** Anthropic Economic Index data is **CC-BY** (code MIT); the coding-study drop is **17 percentage points**; the ranking formula is now explicit; the **deadline sources conflict** (see §12).

---

## 0. Problem statement (the team's)

**One sentence:** *As AI changes which tasks and roles companies need, many firms replace people instead of retraining them. Qart.ai helps companies grow their existing employees into the roles AI is creating. It tracks how AI is changing the work, turns each employee's mistakes on AI-assisted tasks into targeted practice and evidence of skill, and builds personal pathways into the company's future roles.*

**Expanded:**
- AI agents now draft routine finance work (reconciliations, reports), so jobs are shifting from *doing* the work to *checking and owning* AI output.
- Companies face a choice: lay people off and hire for the new roles, or retrain the people they have.
- Retraining is hard, for three reasons:
  - Nobody can see **which employees could grow into which new roles**.
  - Training is generic and goes stale quickly.
  - Employees aren't trained to catch AI mistakes.
- Qart.ai makes retraining practical:
  - Employees practise on realistic AI-prepared work, and **their own mistakes become their next lesson** (*"your mistakes are your future skills"*).
  - Their demonstrated skills are compared, transparently, with how the company's roles are changing under different AI adoption scenarios.
  - Each person gets a time-budgeted pathway and **chooses their own direction**.
  - HR sees aggregated readiness, to plan training capacity instead of headcount cuts.
- The system **recommends; people decide**. It never makes hiring, promotion or dismissal decisions.

**PRD draft for section 2.1 "The Problem Context" (≤250 words; edit it into your own words before submitting):**
> AI is changing work faster than companies can retrain their people. In Malaysia, 56% of professionals already use AI at work, yet only 26% have received formal training (Hays 2025), and MOSTI estimates over 600,000 workers will need reskilling within three to five years. TalentCorp identifies around 620,000–697,000 jobs as highly affected by AI, digitalisation and the green economy. When roles change, many firms default to cutting staff and hiring new skills, losing experienced people and their knowledge.
>
> Finance operations show the problem clearly. AI agents now prepare reconciliations and reports, but their output is not reliable on its own: on the FinBalance reconciliation benchmark, leading models reached at most 46% exact final balance-sheet accuracy, often producing plausible entries unsupported by documents. In ACCA's 2026 survey, 93% of finance professionals were concerned about AI output accuracy and 72% reported basic or no generative-AI proficiency. Employees are now expected to review AI work like seniors, but most were never trained to, and seniors have no time to coach everyone.
>
> Without a way to see which employees can grow into the new roles, and training that adapts to each person's real mistakes, companies cannot retrain at scale, and workers lose the chance to move into better, AI-era jobs. This affects decent work and lifelong learning (SDG 4.4, 8.5).

*(About 230 words. Check each number against its source before submitting.)*

---

## 1. The idea in one paragraph
As AI agents prepare more finance work (reconciliations, month-end reports), employees must judge whether that output is right, and many can't yet. **Qart.ai is a web app that a company's HR/L&D team would deploy so every employee can practise reviewing AI-prepared finance work, build evidence of the review skills they can show, and see how those skills relate to the company's future roles.**
- Employees review AI-prepared reconciliations. They try alone first; if stuck, a companion offers stepped help (question → hint → explanation → answer). The amount of help needed is recorded as **evidence**.
- Independent **check-in cases** show whether a skill holds without help.
- Each employee sees their evidence, a **traceable explanation** of how AI adoption assumptions change the skills each internal role needs, and a **time-budgeted learning path**. **They choose their direction.**
- HR sees **only aggregated** readiness for training and capacity planning.
- The companion's checking procedure can be improved by an optimiser, **only after it passes fixed acceptance tests and a senior approves it**.

**The hackathon prototype uses synthetic employees, a synthetic company and synthetic work.** A real deployment would use real work cases, and that needs separate validation (§10).

---

## 2. The problem: finance-first evidence
| Evidence | Source |
|---|---|
| On the FinBalance benchmark, six LLMs reach **at most 46% exact final balance-sheet accuracy** (a strict measure on that benchmark's multi-document reconciliation tasks, not general accuracy on finance work). Models *"recover numerically plausible entries but fail to bind them to supporting documents"*. There is a 26–41-point gap between the balance sheet they report and the one their own entries produce | **FinBalance** benchmark, arXiv 2606.15949 (Jun 2026) |
| Models closing a real company's books stay within ~1% after month one but **compound errors to >15% divergence** over time | Penrose Labs AccountingBench (vendor research) |
| No general-purpose LLM cleared **70%** on classifying 17,792 real small-business transactions | Digits white paper (vendor) |
| Accounting benchmark: every model **failed at least one-third** of 101 tasks (incl. bank reconciliation, month-end close) | DualEntry 2026 (vendor, commercial interest; treat with caution) |
| **93%** of 1,600 finance professionals are at least moderately concerned about AI output accuracy (67% highly). **72%** report basic or no GenAI proficiency. 41% train in their own time | ACCA / CA ANZ *Enabling Finance Insight*, Jul 2026 |
| 72% of accounting professionals fear GenAI could produce errors or wrong decisions | ICAS, Mar 2026 |
| Auditors are **less sceptical when relying on automated tools** than on a colleague's identical work. A **counter-argument mindset** reduces this | Peters, SSRN working paper (2022). Motivates our "what evidence would change the conclusion?" coaching |
| Audit firms manage deskilling and automation bias through **upskilling early-career auditors** and controlled deployment | Seethamraju & Hecimovic, HICSS-58 (2025) |
| Professional bodies now list **AI review judgment** as an early-career skill | AICPA *Profession Ready* (Sep 2026); ACCA ethics report (Oct 2026) |
| AICPA/CIMA survey: **61%** of 1,446 finance leaders rank **on-the-job training** highest for tech upskilling | AICPA/CIMA, Dec 2025 |
| Malaysia: 56% of professionals use AI at work, only **26%** trained. 600k workers need reskilling. GBS/shared services ~150–163k workers, **24% of roles highly AI-impacted** | Domain 1 brief (Hays 2025, MOSTI); govt-commissioned GBS study (2026) |
| **Motivation only (not finance):** an AI-assisted coding group scored **~17 percentage points lower** on a mastery quiz (≈50% vs ≈67%). But 673 IT apprentices gained capability without comprehension loss in a well-designed setting. Early-career employment in AI-exposed jobs is 19% below expected | Anthropic RCT (Jan 2026); Stanford working paper (Oct 2026); Stanford Digital Economy Lab (Aug 2026) |

**What this supports:** AI-prepared finance work contains plausible but unsupported errors, practitioners are worried and under-trained, and work-integrated training is preferred. **What it does not establish:** that our approach improves finance employees' review skill. That is the core hypothesis to validate (§10).

---

## 3. Use case
- **Future deployment:** a company's HR/L&D team deploys it for a finance-operations team (often in shared-services centres) that has introduced AI agents for reconciliations. Employees use it on real work and practice cases.
- **Hackathon prototype:** synthetic company (Kopi Kita Sdn Bhd), synthetic staff (Aina, 23, new hire; Siti, 41, long-serving clerk), synthetic cases.

| User | Gets | Does not get |
|---|---|---|
| **Employee** | Practice and review support, their own evidence trail, role relevance, a learning path. **Owns their record**; may share a chosen evidence portfolio | — |
| **Senior reviewer** | Reviews the companion's sessions *with permission*; approves or rejects playbook changes | No individual career decisions |
| **HR / L&D** | **Aggregated** readiness by skill (groups under 5 suppressed: this *reduces* re-identification risk but does not guarantee anonymity), training demand under each scenario, capacity planning | **No named "who should move where" lists**, and no individual recommendations unless an employee shares a portfolio |

**Moment of need:** *"The AI says this account reconciles after a small 'rounding' adjustment. Should I sign off?"*
**"Future roles"** means future internal roles; the employee is growing at work. **The system never makes promotion, hiring or dismissal decisions.**

---

## 4. One workflow, precisely: month-end bank reconciliation review
**Workflow:** an AI agent prepares the October bank reconciliation (ledger vs bank statement, matched items, proposed adjustments, a claim such as "reconciles"). The employee must **sign off, correct, or escalate**.

**Skills** (observable in this workflow only):
| skill_id | Observable behaviour in a case |
|---|---|
| `recon_to_source` | Traces the balance to bank lines and documents |
| `duplicate_detection` | Identifies a double-counted entry |
| `cutoff_timing` | Correctly treats timing items (deposit in transit, period cut-off) |
| `unsupported_adjustment` | Challenges a manual adjustment with no supporting document |
| `fx_conversion` | Detects a wrong conversion rate |
| `transposition_check` | Spots a keying error (1,520 vs 1,250) |
| `escalation_judgment` | Chooses the right action (sign off / correct / escalate) |
| `ai_output_review` | Asks for the evidence that would change the AI's conclusion, including when the AI raises a **false alarm** |

**Cases:** each includes **clean cases** (must not be flagged) and **plausible alternative explanations** (e.g. a legitimate timing difference that looks like an error). They are reviewed by someone familiar with reconciliation before the demo.

---

## 5. Evidence model (not a "mastery score")
**Observable event per case:** case id and difficulty · what the employee decided and which rows they flagged · help level reached (0 none · 1 question · 2 hint · 3 explanation · 4 answer shown) · whether the outcome matched the case's known answer · flags for **companion error** (the companion said something wrong or unsupported), **ambiguous case**, or **data issue**.

**Interpretation rules** (explicit, testable, shown to the employee):
- Help level is **evidence, not a measurement**. A success after a hint is weaker evidence than an independent success, but difficulty, unclear instructions and companion mistakes also affect performance.
- **Events flagged as companion error or ambiguous don't count** toward or against a skill.
- **States:**
  - **Insufficient evidence:** fewer than 2 counted events on the skill.
  - **Observed with help:** at least one success that needed help ≥1, or mixed results.
  - **Demonstrated independently *on these cases*:** ≥2 independent successes (help 0, incl. ≥1 check-in) on **different cases**, in **separate sessions**, with no independent failure since.
  - **Self-reported:** only the intake claim so far.
- **"Demonstrated" means on the listed cases. It does not mean lasting mastery.** The UI shows the cases behind each state (an evidence trail) and says why the state changed.
- A probabilistic estimate (Bayesian knowledge tracing with help-dependent guess rates) is used **internally to order practice**. Its parameters are **provisional assumptions without learner data**, disclosed in the app and docs. **No mastery percentages are shown to users.**
- **Reality gauge:** self-reported confidence next to the evidence state (e.g. "you rated 8/10; evidence: observed with help on 2 cases").

---

## 6. From trends to internal roles: three separated layers
This is the most important reasoning step, so each layer is labelled in the UI.

| Layer | What it is | Example | Status |
|---|---|---|---|
| **A. External evidence** (dated, public) | What public data shows about AI use on related tasks and AI-related hiring. **Usage ≠ replacement** | Anthropic Economic Index: AI usage share and automation vs augmentation on bookkeeping/accounting tasks (CC-BY, dated release) · Indeed AI-postings share (9 countries, not Malaysia) · HN job-post skill mentions | Evidence, with source + date |
| **B. Company adoption assumptions** (explicit, editable by HR) | Which tasks the company's AI agent does, and how output is reviewed, **under each scenario** | *Assistive:* AI drafts matching; humans prepare adjustments and sign off. *Agentic:* AI prepares the whole reconciliation; humans review, investigate exceptions, decide | **Assumptions**, informed by A but chosen by the company (synthetic in the prototype) |
| **C. Employee evidence** | What this employee has shown in cases | §5 states | Evidence, per employee |

**Role requirement card** (shown for each role and scenario):
1. The role's **tasks** (from O\*NET 31.0 occupations it is based on, cited).
2. Who does each task under the scenario (**human / AI drafts + human reviews / AI**), from layer B.
3. Resulting **skill weights**: each skill's base importance (from the role's tasks), adjusted by a documented rule. When a task moves to "AI drafts + human reviews", weight shifts from *execution* skills (e.g. matching) to *oversight* skills (`ai_output_review`, `escalation_judgment`). The size of the shift is set by the scenario assumption, **not by the external data alone**.
4. **"Why":** the layer-A evidence that informed the assumption (with source/date) and the assumption itself.

A new external snapshot can make HR **review** an assumption. The app shows the diff and a suggested review, and **the human updates layer B**. In the prototype, the demo shows one dated snapshot change → suggested assumption update → accepted → weights and rankings change, **labelled as historical data replay**.

**Ranking formula (explicit, additive; effort is a penalty):**
```
For employee u, role r, scenario s:
  coverage(u,r,s)      = Σ_k w_{r,s,k} · credit(state_k)  / Σ_k w_{r,s,k}
                         credit: demonstrated=1.0 · observed_with_help=0.5 · self_reported=0.2 · insufficient=0
  confidence(u,r,s)    = share of weighted skills with ≥2 counted events
  interest(u,r)        ∈ [0,1]  (overlap of stated interests with role tags)
  effort(u,r,s)        = estimated hours to close gaps / (weekly_hours × 12), capped at 1
  score = 0.55·coverage + 0.20·confidence + 0.10·interest − 0.15·effort
```
Weights are declared design choices. A ±20% sensitivity check is reported. **The score is a suitability indicator, not a probability of getting a role.**

**Learning path:** chooses practice and free or HRD-claimable resources within the weekly hours, respecting prerequisites, minimising the **worst-case remaining weighted gap across both scenarios**. Coverage of a resource is an assumption until evidence confirms it.

---

## 7. Self-improvement: a hard boundary
- **The only thing it can change:** the companion's **diagnostic playbook** (the ordered checking instructions it follows). It cannot change hint sequencing, retrieval rules, the grader, the skill rules, the acceptance tests or the approval step.
- **Data separation:**
  - **Optimisation set:** cases and variants the optimiser may learn from.
  - **Acceptance set:** **independently authored cases with different reasoning patterns** (different error mechanisms and case structures, not just changed amounts or names of optimisation cases). Never shown to the optimiser. **Fixed criteria in code** (root-cause accuracy, false alarms on clean cases, valid row citations).
  - **Independence matters more than count.** Perturbed variants are useful for robustness checks, but they don't replace independent cases.
  - **Don't tune against acceptance results repeatedly:** run each candidate once. If the acceptance set ends up guiding changes, it has become a development set. Keep a small **final untouched set** for the numbers we report in the PRD.
- **Gate:** candidate vs current playbook on the acceptance set, plus regression checks → **senior approves or rejects** → versioned, with one-click **rollback**.
- **Claims:** results are reported as counts on **synthetic variants** (e.g. "acceptance: 14/20 → 17/20, no regressions"). **This does not show broad improvement.** A rejected patch is still a valid demonstration of the gate.

---

## 8. What we will demonstrate (instead of novelty claims)
1. **Assistance-aware evidence:** independent vs helped successes are recorded and shown, with the cases behind each state.
2. **Independently checked practice:** a missed error leads to targeted practice and a no-help check-in.
3. **Traceable scenario changes:** every change in role requirements points to an assumption and a dated source.
4. **A tested improvement gate:** a playbook change is measured on held-out acceptance cases, approved or rejected by a senior, and reversible.
5. **Grounded companion:** it checks with tools, and every row or amount it cites exists in the case.

Related products (for honest comparison, not "nobody does this"): Forage (employer job simulations), Symphony / Solidroad / TailoredSim (AI simulations and role-play), Workera (skills assessment, voice mentor), Microsoft People Skills (skills inferred from work activity), Eightfold / Gloat (internal mobility), MyMahir (national skills explorer). We compare on the mechanisms above **without claiming what they lack** unless verified.

---

## 9. Build strategy: a working base first, then shippable increments
**Principle (team decision):** *a deployed base with some features beats a perfect plan or nothing.*
- Build the base, deploy it, then add one increment at a time.
- **Every increment ends deployed on Replit and committed**, so whatever we have at any moment is submittable.
- Risky features are **timeboxed spikes**: try them; if they don't work within the timebox, drop or postpone them, write one line in `docs/decision_log.md`, and move on.
- We adjust the plan at each checkpoint based on real progress.

| Increment | Contents | Goal / timing | Rule |
|---|---|---|---|
| **0: Base** | Deployed app · intake · **one case** end to end (text companion with stepped help) · event → evidence rules → skill states · recommender with requirement card (static assumptions v1) · path · SDG tags · one dated snapshot shown with source/date | All six must-haves present at a minimal level. **Target: Thu 22 midday** | Must |
| **1: Golden journey core** | case_003 → targeted case_006 → check-in · next-case targeting · path revision traced to events · provisional state messaging | **Target: M1, Thu 22 evening** | Must |
| **2: Evidence → assumption → recompute** | Ingest the newer dated snapshot through the pipeline → suggested assumption review → HR (synthetic) approves → requirements and recommendations recompute with a visible diff | **Target: Fri 23 midday** | Must (the brief's success test) |
| **3: Trust checks** | Clean case + AI false-alarm case · evaluation runner (acceptance counts vs text-only baseline) | **Target: Fri 23 afternoon** | Must (numbers for the PRD) |
| **S1: RunPod spike** | Embeddings + reranker endpoint used in course/role retrieval | **Timebox 3 h** (Thu/Fri) | If it fails: keep CPU retrieval, declare that no GPU work was done, and ask organisers whether RunPod proof is still required |
| **S2: Voice spike** | Browser speech with interruption (§12) | **Timebox 2 h** (Fri) | Must pass the interruption tests or it's dropped; text stays |
| **S3: Improvement gate spike** | One playbook optimisation cycle → acceptance → senior approve/reject → rollback | **Timebox 4 h** (Fri) | If unreliable: show a recorded, labelled run, or leave it for the Upgrade Round |
| **4: Polish** | HR aggregate summary · senior console · sources page · demo mode | Fri evening | Whatever fits |

### The golden journey (consistent with the evidence rules in §5)
1. Aina's profile: she rates herself 8/10 on adjustments.
2. **case_003:** the AI claims "reconciles" after a "rounding" adjustment. Aina signs off, and **the grader shows she missed it.** The companion walks her back with stepped help, and she finds the error at the hint level. Event: *missed, then found with hint*.
3. **Targeted practice:** the next case is chosen for `unsupported_adjustment` (case_006). She catches it after one question (help 1).
4. **Independent evidence (check-in, no help):** she catches it. The state shows ***observed with help, with 1 of 2 independent successes***. **It is not yet "demonstrated".** The app says why: "needs one more independent success on a different case in a separate session."
5. **Visibly revised pathway:** the adjustments *learning* module is replaced by **one confirmation check-in** scheduled for a later session, and the next gap moves up. The ranking updates; each change is traced to her events.
   - *Optional, if time:* a second check-in in a new, clearly labelled session → ***demonstrated independently on these cases*** → the confirmation step disappears.
6. **Updated external evidence:** ingest the newer dated snapshot through the pipeline → the diff shows the changed signals → **suggested assumption review** → HR (synthetic) **approves** → the role requirement card shows the task-allocation and weight change → recommendations recompute. Labelled "historical data replay". *(A scenario toggle alone does not show updated evidence; both are shown.)*
7. **Trust checks:** a clean case signed off correctly, and the AI false-alarm case handled. The system doesn't "flag everything".

**LATER (Upgrade Round / finals):** more case types · fairness twin-test UI (the test itself runs in evaluation) · BM/Chinese · browser extension · second field · career-centre mode · employee-shared evidence portfolio.

---

## 10. What the prototype demonstrates vs what still needs validation
| Claim | Prototype demonstrates (synthetic) | Still needs validation |
|---|---|---|
| Cases are realistic | Reviewed by one person familiar with reconciliation | Broader practitioner review; real (anonymised) case patterns |
| Companion diagnoses well | Accuracy and false alarms on synthetic acceptance variants vs a text-only baseline | Performance on real AI-prepared reconciliations |
| Stepped help preserves learning | The ladder works as designed; evidence is recorded | Whether finance employees' **independent review accuracy improves** over N sessions (pilot) |
| Evidence rules are sensible | Transparent rules, unit-tested transitions, evidence trail | Calibration of rules and parameters with learner data |
| Role requirements follow trends | Traceable chain: dated source → explicit assumption → weights → ranking | Whether assumptions match real company deployments and future demand |
| Learning path is useful | Constraint satisfaction, robustness across scenarios | Whether recommended resources build the skill |
| Self-improvement helps | Gate works; counts on acceptance variants | Gains on real cases; long-run drift |
| Fair | Rankings ignore demographics (twin test) | Fairness on real populations and data |
| HR planning value | Aggregated view mechanics | HR usefulness and privacy acceptance |

---

## 11. Hackathon fit (verified against the Drive documents)
- **Domain 1:** Main SDG **4** (targets **4.4**, 4.3); relevant 5, 8, 9, 10; targets 8.2, 8.5.
- **Six must-haves:**
  1. Intake + evidence.
  2. Dated signals with source/date and diff.
  3. Explainable role score + gap.
  4. Ordered, time-estimated free/HRD path.
  5. SDG tags per role and skill + path contribution.
  6. Two scenarios labelled as estimates.
- **Rules:** synthetic/public data only · cite sources; no invented jobs, courses or statistics · models declared · humans decide · no full course creation.
- **Success test:** profile → ranked roles + path in minutes; **visible change when trend data changes**; meaningful SDG links.
- **Rubric:**
  - **Innovation:** the five demonstrated mechanisms (§8).
  - **Fit:** the whole chain + humans in charge.
  - **Feasibility:** the golden journey live, plus hardest risk and fallback.
  - **Clarity:** one workflow, one persona, one story.

## 12. System, data and stack (unchanged features, corrected details)
- **Form:** one web app (Employee · Senior · HR summary) with synthetic accounts.
- **Components:** intake · workspace · companion (tools + stepped help + playbook) · grader (only module reading the answer key) · event recorder · evidence rules + provisional estimate · trend snapshots · company assumptions (layer B) · role catalogue (O\*NET-based) · recommender · scenario engine · path planner · course catalogue + retrieval (reranker on RunPod) · SDG mapper · senior console + optimiser + acceptance runner · HR aggregate summary.
- **Data and licences:**
  - Anthropic Economic Index: **data CC-BY, code MIT**, attribution required.
  - Indeed Hiring Lab AI tracker: cite.
  - HN "Who is hiring": public API.
  - O\*NET 31.0: CC BY 4.0.
  - Courses: URLs + retrieval dates.
  - Everything else synthetic.
- **Stack:** React + TS · FastAPI · Postgres/SQLite · **Replit** (compulsory) · **RunPod** (embeddings/reranker, with screenshots) · provider-agnostic LLM · OR-Tools · GEPA or a simple reflective loop.
- **Voice is a spike, not an assumption.** Browser speech APIs are a prototype option with **compatibility limits**: speech recognition is not available in every browser (see MDN's SpeechRecognition compatibility table) and may rely on a remote service. The 2-hour estimate is untested. **Pass criteria:**
  1. When the user starts speaking, playback stops within about 0.5 s.
  2. The stale companion response is cancelled, including any pending action, not just muted.
  3. The interruption is transcribed and answered in context.
  4. Text chat keeps working throughout.
  
  If these don't pass in the timebox, voice is dropped for the preliminary.
- **Deadline:** the Participant Handbook says **25 Oct 07:59 AM MYT**; the public FAQ shows **25 Oct 11:59 PM MYT**. **Treat the earlier time as binding until the organisers confirm on Discord, and submit by ~22:00 on 24 Oct either way.**

## 13. Demo (5–7 min)
1. Moment + finance evidence, with qualifications:
   - FinBalance: "at most 46% exact final balance-sheet accuracy on that benchmark".
   - ACCA/CA ANZ: 93% at least moderately concerned about AI output accuracy; 72% basic or no GenAI proficiency.
2. Golden journey steps 1–5, ending with "1 of 2 independent successes" and the confirmation step on the path.
3. Updated external evidence: ingestion → suggested review → approval → recompute, plus the scenario toggle.
4. Clean case + AI false alarm.
5. *(if the spikes passed)* the improvement gate and/or voice interruption.
6. Limits and the Phase 2 validation plan.

## 14. Impact Framework (PRD)
- **Target:** SDG **4.4**.
- **Baselines:** 56% use AI / 26% trained (Hays 2025) · 72% basic/no GenAI proficiency in finance (ACCA/CA ANZ 2026) · 35.2% graduate underemployment (DOSM Q2 2026).
- **Prototype KPIs:**
  - Companion acceptance accuracy and false-alarm rate vs a text-only baseline.
  - Evidence-rule tests passing.
  - Time to path.
  - Gate results.
- **Phase 2 target:** a pilot with finance/accounting students: **independent error-catch rate on unseen cases before vs after N practice sessions**, set after a first baseline measurement. No job-outcome claims.

## 15. Timeline and checklist
See `team/` files:
- **M0** Wed 21: contract + repo + start.
- **Increment 0** deployed Thu 22 midday.
- **C1** Thu 14:00.
- **M1** Thu 21:00: Increment 1, golden journey steps 1–5.
- **C2** Fri 14:00: Increments 2–3 progress; decide which spikes continue.
- **M2** Fri 22:00: full journey steps 1–7 + any spikes that passed; feature freeze.
- **Submit** Sat 24 by ~22:00.

**Adjust at every checkpoint:** if something is behind, ship what works and cut from the bottom of §9's table.
Deliverables: PRD (word limits + Impact Framework) · deck · live link · Tech & Tools Declaration (Replit proof, RunPod screenshot) · public Apache-2.0 repo with steady commits · 5–7 min YouTube video · workshops completed.
