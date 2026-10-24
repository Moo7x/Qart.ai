# Personal journey

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

**Calculation.** `src/match/engine.py` computes
`fit = 100 × sum(weight × min(claimed / required, 1)) / sum(weight)`.
Unknown levels contribute zero but remain "not stated"; essential gaps mean "longer route".
A scenario shifts a non-essential weight by `w' = w × (1 + d × s × a)`: d is the skill's
declared direction (routine −1, AI-complementing +1), s the scenario intensity (moderate 0.5,
fast 1.0) and a the observed automation-style share of AI use. a is task-level where it can be:
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

**Plain-words explanation.** `src/match/explain.py` (Roles, on click) gives gpt-4o-mini the
computed facts of one role result and asks for a few sentences, each citing the facts it uses.
Code drops sentences with numbers (digits or words), forecast or promise words, or no valid
citation; the cited facts, written by code, are shown under each sentence. No key, an error or no
valid sentence gives a labelled template of the facts. Market evidence is not given to the model.

**My goal.** `src/goal/posting.py` (page "My goal"): the person names a target role and may paste
a public job posting. gpt-4o-mini lists its requirements under a strict schema, each with a quote
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
unstated skills at proficient (assumption-based, not a statistical interval); the most valuable
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
