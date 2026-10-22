# Project rules for coding agents: Qart.ai

Qart.ai (SDC Hackathon 2026, Domain 1: Aiversecity Future-Ready Workforce) is a web app a company deploys so employees practise reviewing AI-prepared finance work (bank reconciliations) with a stepped-help companion. Their mistakes and successes become evidence of skill. Dated public trend data plus explicit company AI-adoption assumptions drive explainable future-role matching and a time-budgeted learning path. The goal is to train people as AI changes the work, rather than replace them.

Read first: `PROJECT_PLAN.md`, `team/00_SHARED_CONTRACT.md`, and the person file for whoever you are helping (`team/PERSON_A_ENGINE_AND_DATA.md` or `team/PERSON_B_APP_AND_COMPANION.md`).

## Hard rules (hackathon)
- Synthetic or public/open data only. Never add real personal data or real CVs.
- Never invent jobs, courses or statistics. Every recommendation or claim shown to users carries a source + date. If you cannot verify a URL, mark the item `"verified": false` for a human to check.
- Humans decide. The system recommends; it never makes hiring, promotion or dismissal decisions.
- No secrets in code or commits. Read keys from environment variables only; keep `.env.example` with names only.
- Respect the JSON contract in `team/00_SHARED_CONTRACT.md` / `schemas/`. If a change is needed, stop and tell the human (contract changes need both teammates).
- Only edit the folders owned by the person you are working for (contract §1). Shared files (`src/main.py`, `schemas/`) only with care.
- Never show users a mastery percentage. Show evidence states, the cases behind them, and why they changed.
- Label every number as evidence (dated source), assumption (company layer B / declared parameter) or synthetic.
- HR sees aggregates only (groups under 5 suppressed, which reduces but does not eliminate re-identification risk). Individual recommendations are employee-facing only.
- The optimiser may only edit `src/companion/playbooks/`. It must never read `eval/acceptance/` or change grading criteria.

## Engineering rules
- Small, reviewable changes; one feature per commit; meaningful commit messages (e.g. `engine: add evidence-state rules`). Commit often. Never one giant commit. Follow the qart-git-workflow skill (commit size, messages, no force-push/squash, never commit data/raw, .env or secrets).
- Prefer simple, explainable logic. Comment the "why" of every formula, weight and threshold.
- Add/maintain tests (`python -m pytest`). Keep them passing before each commit.
- Log every new library, model, dataset or API with its licence in `docs/DECLARATION_LOG.md`, and decisions in `docs/decision_log.md` (skill: qart-declaration-log).
- Run the qart-contract-check skill before committing changes to endpoints or contract objects.
- Follow the qart-code-standards skill for all code (typed, linted with ruff, tested, no magic numbers, formulas documented).
- After finishing or changing a module, update its explanation doc with the qart-explain skill (docs/explain/).
- The human must understand every component: explain non-obvious code in the commit message body.
