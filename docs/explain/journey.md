# Personal journey

**Why you need this (software evidence):** `src/match/basis.py` prefers a role-specific
TalentCorp page, then linked O*NET tasks, then accepted `onet_technology` observations mapped
through `data/packs/gbs_fa/technology.yaml`; otherwise it says "our assumption". The optional map
loads with the pack and rejects unknown skill ids, repeated categories or missing reasons.
O*NET 31.0 calls its file `software_skills.csv`; older `technology_skills.csv` releases still work.
Each observation groups one US occupation and software category: 2 means at least one example
is flagged In Demand for that occupation, 1 means Hot Technology across occupations only, and
0 means listed without either flag. These codes are not demand percentages or scoring weights.
The explanation names the release, occupation and US scope; a displayed example need not itself
carry the category's strongest flag. Software use does not prove implementation expertise,
Malaysian demand or a learner's proficiency. A new profile starts with the latest snapshot;
existing profiles keep their accepted snapshot until a revision is accepted. Both role gaps
and plan stops use that same snapshot. Nothing here changes requirements, fit scores or levels.

**One person, one plan:** every route that scores roles or plans for a person loads them once
through `src/journey/person.py` (`Person`: profile, destination, accepted evidence). `Person.plan`
always passes the person's claims and situation, and `Person.rank` always orders near-ties by
their interests and chosen SDGs, so `/matches`, `/pathway`, `/tracks`, `/sdg`, `/badges`,
`/future`, `/radar`, `/explain`, the change test and the status totals all use the same plan.

**First-run flow:** `/` always sends visitors to `/start`, including saved-profile users. After building,
the final action opens Overview. Overview's edit action loads existing answers and updates the
same profile without clearing its destination. Start over forgets the browser's profile key and
resets the scenario; it does not delete database records. Evidence pages remain publicly accessible.
Role/task/interest/goal example chips derive from the verified pack; task examples cite O*NET.

**Fix-round diagnostics:** an unhandled API error returns a random reference. Logs contain only
the route template, exception class and code locations, never exception values or SQL parameters.
The opt-in `tests/test_postgres_journey.py` checks onboarding on a disposable PostgreSQL database
specified by `QART_TEST_POSTGRES_URL`. A passing local check does not verify Replit's schema/version.

**Task-to-skill search:** uses the shared RunPod async queue (30-second interactive budget),
validates vectors and caches skill text rather than ID alone. Measured stages and engine/fallback
notes are returned. Suggestions are not claims: the person selects skills, then sets levels.

**What and why.** A synthetic CV or questionnaire becomes editable skill claims, scores for all
nine GBS destinations, a person-chosen goal and an ordered free-resource pathway (must-haves
1, 3–6). `src/intake/` scrubs identifiers and checks model quotes; missing services use labelled
keyword/form fallbacks. `src/pack.py` validates the curated skill, role, resource and SDG pack.

**Levels.** `src/levels.py` reads `data/packs/gbs_fa/levels.yaml`: a 0–5 scale (none · novice ·
aware · working · proficient · expert) and, for every skill a destination role requires, five
"I can…" sentences, one per level. The person picks the highest sentence true for their work in the
last two years; level 3 and above need work done, not study. The sentences are our own, written to
the level structure of SFIA 9 and, for finance skills, the Skills Framework for Accountancy (ACRA
and SkillsFuture Singapore) and UF's accounts payable competency; each skill cites its basis and
its TalentCorp page, and stays `status: draft` until the team reviews it. Stored levels keep their
numbers: core requirements stay at 3 ("working"), upskill and support at 2 ("aware").
`python -m src.levels --missing` lists required skills without five sentences. On screen (`web/src/components/LevelPicker.tsx`, onboarding and the best-question box) the person picks a sentence, "None of these" (0) or "Not sure" (unstated, never 0); levels show as stored ("3/5") with labels from `GET /api/pack`, never hard-coded.

**Why this score, and what would raise it.** Each role card on `/matches` (C2) adds a band from
the fit (strong ≥ 75 · good ≥ 55 · fair ≥ 35 · low, `BAND_THRESHOLDS`, an assumption), a range
(low: self-rated and keyword claims one level lower, unstated as none; high: claims as stated,
unstated at working), one component row per requirement (weight, claimed, required, points, and
the CV or check evidence behind the claim), the essentials still short, and "raise": the three
single-skill changes worth the most points, each re-scored exactly. A skill below its need is
tested at the required level, by study if that is within `STUDY_MAX_LEVEL` (2) and by practice
above; a skill already at its level but self-rated is raised by a check, whose points are the rise
in the bottom of the range. Pay (`src/match/pay.py`, C11) shows the OpenDOSM median and mean
monthly wage of the role's occupation group with its year and source, labelled observed and
"not an offer for this role"; it never changes fit, band or rank, and is "not published" until
the series is collected.

**Calculation.** `src/match/engine.py` computes
`fit = 100 × sum(weight × min(claimed / required, 1)) / sum(weight)`.
Unknown levels contribute zero but remain "not stated"; essential gaps mean "longer route".
A scenario shifts a non-essential weight by `w' = w × max(0.1, 1 + d × s × a)`: d is the skill's
declared direction (routine −1, AI-complementing +1), s the scenario intensity (moderate 0.5,
fast 1.0) and a the observed automation-style share of AI use. The floor of 0.1
(`SCENARIO_FACTOR_FLOOR`, declared) keeps a routine weight from vanishing or turning negative at
the strongest sensitivity case (s = 1.5). a is task-level where it can be:
the O*NET tasks linked to that skill in the role's occupation (`data/packs/gbs_fa/tasks.yaml`),
averaged with O*NET importance as the weight; otherwise the occupation's share, and the screen
says which. The transfer from global Claude usage to Malaysian work, the levels and the weights
are declared assumptions, not learned adoption forecasts. Essentials keep their level and
weight. `src/params.py` names each policy value.

**Task view.** `src/match/tasks.py` shows each destination role's linked tasks with four kinds
of evidence kept apart: observed AI use per task (Economic Index), reported deployment (not
collected yet; shown as missing), potential exposure of the role's ISCO-08 occupation (ILO,
an estimate) and expert impact (TalentCorp). It never states that a task is being automated.

**Demand outlook.** `src/match/outlook.py` adds, next to fit but never inside it: the DOSM share
of employees for the role's MASCO major group (reached through its ISCO-08 code) with the
backtest result, the DOSM job-ad share where DOSM names the occupation, which of the role's skills
TalentCorp lists as in demand, and whether MyCOL 2024/2025 lists the occupation as critical.

**Radar.** `src/match/radar.py` (Overview) draws the person's chosen role, or best-fitting role
until one is chosen: claimed level, needed level and level after the pathway (estimate) per skill,
with the scenario emphasis (assumption), the observed AI use behind it and TalentCorp's in-demand
flag (expert) kept apart. Below it are the existing field signals for the person's current
occupation (its DOSM major group, job ads, AI use), so two CVs get a different radar focus.

**Plain-words explanation.** `src/match/explain.py` (Roles, on click) gives gpt-4.1-mini (`LLM_MODEL`) the
computed facts of one role result and asks for a few sentences, each citing the facts it uses.
Code drops sentences with numbers (digits or words), forecast or promise words, or no valid
citation; the cited facts, written by code, are shown under each sentence. No key, an error or no
valid sentence gives a labelled template of the facts. Market evidence is not given to the model.

**My goal.** `src/goal/posting.py` (page "My goal"): the person names a target role and may paste
a public job posting. gpt-4.1-mini lists its requirements under a strict schema, each with a quote
code checks against the posting (PII scrubbed first), a pack skill or "other", and "required" only
when the posting says so; otherwise keyword matching, labelled. Coverage is counts of this posting
("covers 2 of 6, essentials 1 of 2") with unstated and out-of-catalogue requirements apart, using
level 2 where the posting states none (declared). Stepping stones are verified roles sharing the
posting's skills, with the person's fit and learning that serves both. No scraping or applying.

**Journey screens.** Navigation follows My goal → My options (Roles) → My plan (Pathway) → What
changed, with Trends, Any occupation and Live intelligence under Evidence. Overview shows what is
changing in the person's current job (its occupation's evidence). Roles compares two roles side by
side, links each role to external job searches (JobStreet by title, the MYFutureJobs search page;
Qart does not read or check openings), and tailors one line by situation: graduates see TalentCorp's
listed ways in, switchers see which stated skills carry over. Pathway shows a clickable
prerequisite roadmap (done, ready, needs a prerequisite) and three progress measures kept apart:
plan completion (self-reported, saved per profile in `src/journey/progress.py`), requirement
coverage (changes only when the person edits their levels) and skills still to tell; plus this
week's steps within the weekly hours, and pause/resume that never lowers anything.

**Study versus practice.** `src/pathway/planner.py` gives study a declared ceiling: material
covering a skill reaches level 1 from 1 h (`LEVEL1_MIN_HOURS`) and level 2 only from 20 h with a
hands-on item (`LEVEL2_MIN_HOURS`; the shortest recognised programme found was 19 h), never above
`STUDY_MAX_LEVEL` (2). Courses are added shortest first until study reaches the most it can give;
courses that would not change that level are left out. Levels 3 and 4 come from practice steps
(`data/packs/gbs_fa/practice.yaml`): a work task per level with a declared week range (estimate,
to agree with a manager) and what to describe in a progress check. Each plan reports study hours,
practice weeks as a range, and two fit ranges (after study; after study and practice) by the C2
rule with planned levels counted as unevidenced. With today's catalogue no course is marked
hands-on, so study reaches level 1 and the plan says the rest needs more material or practice. Steps unlock
in order (`apply_progress`): a course after the one before it is done; a practice step after its
skill's study steps. A practice step is complete when the skill's claim reaches its target,
labelled "checked" (accepted progress check) or "self-rated"; "continue anyway" stores it as
skipped (`journey_skipped`), shown as "continued anyway, not done".

**The plan adapts to the person.** AI basics are skipped when the person shows AI or automation
work with evidence: any of prompt engineering, automation, advanced technology integration or
data management claimed at level 3 or above from a CV sentence or an accepted progress check
(`AI_BASICS_SKILLS`, `AI_BASICS_SKIP_LEVEL`); the plan says "Skipped: your CV shows ‘…’" and
keeps the track for "Show AI basics anyway". Students and switchers always see them. A skill at
level 2 or above (the most study gives) goes straight to practice: no course, beginner or other,
is planned for it, and it is never listed as "no verified free course yet".
Every adjustment is listed under "Adjusted for you" with its rule.

**My plan as three tracks.** `src/pathway/tracks.py` (GET `/api/profiles/{id}/tracks`) shows the
plan as three rows: (1) AI basics, a declared foundation everyone sees first (what generative AI
is, prompting at work, using AI responsibly, data basics); (2) reskilling without AI, the role's
gaps in finance, business and green skills; (3) reskilling with AI, its gaps in data and digital
skills (`params.AI_TRACK_KINDS`, following TalentCorp's skill clusters). Each skill is a node;
clicking it opens three temporary windows: courses (planned ones count towards hours and fit),
YouTube videos and articles. Videos and articles come from `data/packs/gbs_fa/resources.yaml`:
YouTube title and channel checked through the public oEmbed endpoint, length and date from the
watch page, articles loaded and title-matched, all on 2026-10-24; they are links only and never
counted in hours or fit. A node unlocks when the earlier nodes of its track are done.

**With AI or without.** The comparison plans the role twice with the same planner and course
rules: over the non-digital skills only, and over every skill plus the AI-basics courses. The same
engine scores fit under both scenarios; it shows hours, weeks, courses, fit after and fit gained
per 10 hours. Plan hours have one definition, the planned study steps: the with-AI time is shown
as "X h plan + Y h AI basics" (`plan_hours`, `ai_basics_hours`), and the plan page adds
"+ Y h AI basics" beside its total instead of folding it in. "With AI" means also learning the AI-related skills, not studying with an AI tutor;
no study claims a speed-up from AI tutoring for this audience, so none is assumed.

**Job posts.** Each role has a "See job posts" window with live searches on JobStreet (Malaysia
and Kuala Lumpur), Indeed Malaysia and MYFutureJobs; the URL patterns were opened in a browser on
2026-10-24 and returned real postings for the titles. LinkedIn (sign-in wall) and Hiredly (ignores
the search term) were left out. Qart links only: it does not copy, rank or check postings, since
recruitment integrations are outside the brief.

**Feedback.** `src/feedback/service.py`: "Report a problem" on roles, courses and posting lines
stores the kind, the target and the version the person saw. Preferences ("not my goal",
"schedule does not work") apply to that person only and at once. Error reports go to the admin
review on Live intelligence; a "course unavailable" report carries a bounded correction, which is
first run on fixed synthetic regression profiles for every destination (plans changed, essentials
left without a course), then released for everyone or rejected, with a logged decision. Nothing
is learned automatically and the system never edits its own code or weights.

**CV draft.** `src/cv/draft.py` (page "My CV") builds a draft only from confirmed data: a headline
from the current role and chosen goal, skills with the person's own ratings, the sentences quoted
from their CV, and courses they marked done under Learning (never as experience). Each draft is
compared with the last accepted version (new lines marked, removed lines struck through); the
person accepts it as a new version and can download it as text. Nothing is invented.

**Bahasa Malaysia.** `web/src/i18n.tsx` adds an English / Bahasa Malaysia switch (remembered in
the browser) for navigation, onboarding, page titles and main actions. Texts are keyed by their
English wording, so anything untranslated stays English. Evidence, source passages and numbers are
not translated. The Malay text was written by the team with AI assistance; a native-speaker review
is still pending and the switch says so. Occupation matching already accepts Malay job titles
(BGE-M3 on RunPod: 75% of Malay test titles in the top 3).

**Activity and mobile.** Long actions (reading a CV or a posting, matching an occupation, the
plain-words explanation) return the stages the server measured (`src/stages.py`): name, engine,
seconds, and whether a step failed and fell back. While one runs the page shows what it is doing
and the elapsed time (no invented progress bar); afterwards "What happened" lists the stages, e.g.
GPU embedding 20.9 s on a cold RunPod worker, comparison 0.1 s, reranking 2.5 s. On phones the menu
folds into a button so content starts at the top; every page was measured at 375 px without
sideways scrolling.

**Decision support.** `src/match/decision.py`: meters keep coverage (the fit), essential readiness
(below level versus not stated) and profile completeness apart; the fit range recomputes with
unstated skills at working, level 3 (assumption-based, not a statistical interval); the most valuable
question answers each unstated skill both ways and ranks them (essential of the person's goal,
then a change of best-fitting role, then the largest fit swing; weights in `src/params.py`);
sensitivity re-ranks under adoption intensities 0–1.5; what-if recomputes without saving. An
answer is saved as a self-rated claim. `src/pathway/optimise.py` compares, within weekly hours ×
12 weeks, the planner's own order cut at the budget, the exhaustive best set (most essentials,
then projected fit, then fewest hours) and the set whose lower scenario fit is highest. Example:
at one hour a week, a finance-systems goal reaches projected fit 50.0 with the best set versus
22.9 for the simple plan. The best sets favour many short modules because each may add one level
under the declared gain rule; that rule is an assumption, not measured learning.

`src/pathway/planner.py` visits essentials first, selects the shortest useful course, includes
prerequisites once and schedules at the weekly-hours budget. Duration/level rules produce
hypothetical gains, not measured learning outcomes. Some gaps have no verified free resource.
`src/journey/store.py` persists claims and destination, not the full CV or contact fields.

**SDG contribution.** Every skill and destination role has its own SDG links in
`data/packs/gbs_fa/sdg.yaml` (target, one-line mechanism, source). `src/pathway/sdg.py`
(`GET /api/profiles/{id}/sdg`, C4) turns the plan into skills × targets: a study step's hours are
split equally over the gap skills it serves and count toward every target a skill serves, so
per-target totals are not added across targets; practice is a marker, not hours. On
`/pathway#sdg` the heatmap is a table in one violet hue with the hours printed in each cell and
a click opening the reason and source; free learning (4.3) and the role move (8.5) are listed as
path links below it. On `/roles` a roles × targets grid (`sdg_roles` on `/matches`) shows which
targets each role serves, linked or not, with the reason on click.

**Progress events and badges.** `src/journey/events.py` records what a person does as dated
events in `journey_event` (C5): `level_changed` with its source (including the starting claims),
`destination_chosen`, `course_done`, `course_undone` and `step_skipped`, only when something
changed. Badges are derived from these events alone: "First step" and "Skill up" (a rise on a
skill the destination requires) stay once earned; "Essentials ready", "Halfway" and "Plan
complete" show only while true. The plan page shows each badge with the event and date that
earned it. Owner A's progress check records its accepted level through `record_event`.

**Personas.** Four synthetic people (`data/samples/`): Hafiz (graduate), Mei (retail supervisor
switching in), Nur (cash application analyst at risk) and Kavitha (senior reporting analyst).
`tests/test_personas.py` builds each through the API from fixed levels, each quoting their CV,
with no model, and proves results are not hard-coded: at least three different top roles,
Kavitha's top fit above Nur's, AI basics for Hafiz and not for Kavitha, practice for Kavitha
wherever a core skill is short, and every number in the role score (C2) and plan (C3) carrying a
source or a label, including any number added later.

**Report figures.** `python -m scripts.kpis` builds the app offline and writes
`docs/KPI_RESULTS.md`: verified free-course coverage over the pinned Phase 1 set of 37 required
skills (baseline 27/37, target at least 34/37), with skills added later reported apart; the free
share of each persona's plan; the share of C2 and C3 numbers carrying a source or label
(`src/match/labels.py`); and the C10 paired-profile check (`src/match/fairness.py`
`paired_profile_check`, the same identities as the fairness test).

**Fairness.** `tests/test_fairness.py` runs three synthetic versions of one CV that differ only
in name, gender, religion, race, date of birth, marital status and contact details. It checks
that the scrubbed text, the exact messages the language model would receive, the keyword
fallback and the ranked roles, gaps and pathways in both scenarios are identical. The profile
has no protected fields, so none can reach matching later. Limit: only labelled lines and the
name line are removed; a protected fact written inside a sentence ("as a mother of two") stays
in the text the model reads.

**Where.** `src/api/journey.py`: intake, pack, profile, matches, destination, pathway, future
and role-tasks routes. `web/src/pages/{Onboarding,Roles,Pathway,Future}.tsx` consume the real API. Pathway
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

### Opening and saved profiles
The root URL always opens the welcome flow at /start. Saved profiles are resumed explicitly through Continue with my saved profile, opening /overview. All Overview navigation uses /overview. A server 404 clears an obsolete browser profile key; transient failures keep it for retry.


### Career workbook layout and resource windows
Desktop pages use a centred workspace beside the menu; onboarding pairs each question with relevant help. Task examples come only from the selected role's own O*NET occupation (the task crosswalk first, otherwise the already stored occupation catalogue with release/fetch date), and extracted CV quotes prefill an editable task description. Activity results stay on the step that ran the action.

My plan opens with three connected track stations. Full skill labels and explicit next/done/locked/no-planned-course states replace truncated labels. Selecting a skill opens three independently closable, scrollable resource panes. Escape or Close all dismisses them; keyboard focus stays inside the dialog and returns to the triggering node. Completion remains self-reported and does not prove proficiency.

### How Qart decides
1. **Read the profile:** rules remove identifiers from a synthetic CV. OpenAI gpt-4.1-mini (`LLM_MODEL`) extracts allowed skill claims with exact quotes; code rejects unsupported quotes. Without the model, a labelled keyword fallback suggests unrated skills. On both paths, if the CV names an ERP system (`ERP_ALIASES`: SAP, S/4HANA, Oracle, …) and no ERP claim was read, a rule adds one at level 2 with that sentence as evidence, and the note says "added by rule". Skills or tools the model finds outside our list come back as `unmatched` phrases (each checked to be in the CV) and show as "Not in our skill list"; they never change a score, and the keyword fallback says it cannot list them. People review and rate them.
2. **Search:** BM25 or BGE-M3 embeddings on RunPod map task wording to catalogue skills. The wider occupation search also uses the RunPod reranker. Retrieval suggests identities, not proficiency, fit scores or jobs.
3. **Calculate:** accepted Economic Index task/occupation observations feed declared Moderate/Fast emphasis rules. TalentCorp supplies role and skill requirements. Essentials remain fixed. Pure Python computes coverage scores, gaps and rankings for every destination. ILO exposure and DOSM demand/history are separate evidence panels, not extra ingredients secretly added to fit. DOSM projections have their own backtests; they are not forecasts of individual hiring.
4. **Plan:** code orders verified free courses by prerequisites and a person's weekly hours, with target-level SDG mechanisms. Projected gains use declared rules, not measured learning. Three tracks group this same output; their comparison includes AI-basics study time, not a proven AI-tutoring speedup.
5. **Keep control:** course completion is self-reported, never an automatic proficiency increase. New collected evidence proposes a revision; the person accepts it. Role search windows link out to job boards and guarantee no vacancy.

Overview starts with the current role, ranked options, a prioritised essential/weighted gap and the next uncompleted course. Light charts share the Trends components; full radar labels wrap. Job-search windows are available beside role options, future lists, goal alternatives and Overview recommendations. Long source badges wrap on phones. Learning progress saves show failures and block duplicate pending writes; switching scenarios remounts the plan state to avoid displaying an old scenario response.
