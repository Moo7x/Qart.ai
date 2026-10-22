# Project rules for coding agents: Qart.ai

Qart.ai (SDC Hackathon 2026, Domain 1: Aiversecity Future-Ready Workforce) takes a person in
Malaysia from "who I am today" to "where I can be in the AI era". A scheduled intelligence pipeline
collects dated public evidence about AI and the job market from registered sources; code turns that
evidence into task-level change, skill emphasis per scenario, ranked future roles with an
explainable fit score and skills gap, and an ordered reskilling pathway where every role, skill and
step is tagged to an SDG target. People make the decisions.

Read first: `docs/PLAN.md` (product and system design). It is the only source of truth for scope.
Build the **MVP scope** listed at its top first; items marked improvement phase or on hold are not
built until the human says so.

## Scope
- Users: working adults at risk of displacement, fresh graduates / students (also via TVET and
  university career centres), career switchers; later HR / L&D managers (aggregate team view only).
- Field: Malaysian Global Business Services (GBS), finance & accounting only.
- Six must-haves (brief §4): profile intake (CV / form / questionnaire) · updatable AI and job-market
  signal layer showing source and date (hard-coded lists do not count) · ranked future roles with an
  explainable match score and skills gap · ordered pathway with time and free / low-cost resources ·
  every role and skill tagged to at least one SDG with how the chosen path contributes · more than
  one future scenario, labelled as estimates.
- Core SDG targets: 4.4, 4.3, 8.2, 8.5. Others (5, 9, 10, 13 ...) only where the work supports them.
- The app never tutors, hints at answers or grades the user; it shows evidence and options.
- Out of scope (brief §6): full course content, payments, real recruitment integrations.
- Any change of product direction or scope is a question for the human before it goes into code
  or the plan. Do not add, remove or reinterpret features on your own.

## Hard rules (hackathon)
- Public, open or synthetic data only. No real personal data and no real CVs; sample profiles are
  synthetic and labelled.
- Never invent jobs, courses or statistics. The LLM never produces numbers; code computes them from
  stored observations. Every recommendation, role, skill, course and claim shown to users carries
  its source and date. Anything that cannot be verified is stored with `verified: false` and is
  never recommended.
- Name the LLM wherever it is used (OpenAI gpt-4o-mini) and in the declaration log.
- Humans decide. The system recommends; it never makes hiring, promotion or dismissal decisions.
  New evidence only proposes revisions with a diff; the user accepts or declines.
- Label every number shown as **observed** (source + date), **assumption** (scenario rule or
  declared parameter) or **estimate** (forecast). Missing is not zero.
- Keep the four kinds of task-change evidence separate: observed AI use, reported deployment,
  potential exposure, expert impact. No "being automated" verdict from usage alone.
- Essential skills and prerequisites keep their required level in every scenario; scenarios only
  shift emphasis weights.
- A person's skill level is always a claim (CV span or self-rating), never shown as verified.
- PII is stripped before matching. Protected attributes never change a result (paired-profile test).
- HR sees aggregates only; groups under 5 are suppressed.
- No secrets in code or commits. Keys come from environment variables; `.env.example` holds names
  only.

## Engineering rules
- Python 3.12 (`src/__init__.py` stops older versions). FastAPI backend in `src/`, React +
  TypeScript + Vite + Tailwind frontend in `web/`. SQLite locally, Postgres on Replit, through one
  SQLAlchemy Core layer.
- Simple, explainable logic. Every formula, weight and threshold lives in a named, commented
  parameter (what, why this value, and whether it is evidence, assumption or declared parameter).
- Agents and LLM calls: every answer is schema-constrained and validated in code; every fallback is
  visible (`source`, `engine`, `note` fields) and never reported as a model result. Remote services
  (LLM, RunPod) get a time budget and a labelled fallback; no page waits for a GPU cold start.
- The research agent never writes scores. It publishes validated evidence; code recomputes.
- Tests with `python -m pytest`; `ruff` and `mypy` clean before each commit. Tests never call paid
  services: use fakes for LLM, RunPod and network sources.
- Verify every screen against the real API, not only mocks; frontend types match server shapes.
- No hard-coded user ids, role ids or answers in the UI; everything comes from the API or data.
- Log every new library, model, dataset or API with its licence in `docs/DECLARATION_LOG.md`, and
  decisions in `docs/decision_log.md` (skill: qart-declaration-log).
- Follow qart-code-standards for code and qart-git-workflow for commits. After finishing or
  changing a module, update its explanation in `docs/explain/` (skill: qart-explain).

## Git
- Small commits, one change each, plain messages (`area: what changed`). No AI attribution lines
  (no "Co-Authored-By" for tools).
- Never push, force-push, rebase shared branches, `reset --hard`, `clean`, delete branches, or
  change git config or remotes. The human pushes.
- Never commit `.env`, keys, `data/raw/`, databases, `node_modules/`, `web/dist/` or `notes/`.
- Nothing addressed to the human goes in the repository; the repo is written for readers and judges.
