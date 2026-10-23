---
name: qart-code-standards
description: Professional code standards for Qart.ai (Python/FastAPI backend and React/TypeScript frontend). Use whenever writing or modifying code in this repo, and before every commit, so the code stays clean, typed, tested and easy for the team to explain to judges.
---

# Qart.ai code standards

The team must be able to explain every line to judges ("any member can be asked about any part"). Optimise for **clarity over cleverness**.

## Project tooling (set up once, keep passing)
- Python 3.12. `pyproject.toml` with:
  - **ruff** (lint + format; rules E, F, I, B, UP, SIM, N; line length 100)
  - **mypy** (or pyright) in strict-ish mode for `src/`
  - **pytest** config
- Frontend: TypeScript `strict: true`, oxlint.
- Before each commit: `ruff format . && ruff check . && mypy src && pytest -q` (frontend: `npm run lint && npm run build`). Don't commit red.
- A pre-commit hook (`pre-commit` with ruff + a secret scanner such as gitleaks) if available.

## Structure
- One responsibility per module. Computation (`src/evidence/`, `src/match/`, `src/pathway/`) is **pure functions** (no FastAPI, no DB, no network), so it is testable and explainable. Collectors and agents fetch and validate; they never compute scores. Routes only validate, call the computation, and return Pydantic models. Persistence only through `src/db.py`.
- API objects are **Pydantic models**; frontend types mirror them exactly.
- No hidden state: pass inputs explicitly, return outputs explicitly.

## Style
- Full type hints on every function. Small functions (aim for ≤40 lines). Descriptive names (`independent_success_count`, not `isc`).
- **No magic numbers.** Every weight, threshold and parameter lives in a named constant or config file (e.g. `src/params.py`) with a comment: what it is, why this value, and whether it is an *assumption*, *declared parameter* or *derived from a source* (cite it).
- Docstrings (Google style) on public functions: purpose, args, returns, and for formulas the formula itself in plain text.
- Comments explain **why**, not what.
- Errors: raise specific exceptions in the engine; routes translate them to clear HTTP errors (`422` bad input, `404` unknown id). Never swallow exceptions silently.
- Logging via `logging` (no prints) with meaningful messages. Never log secrets or personal data.
- No dead code, no commented-out blocks, no unused imports, no TODOs without an owner and a reason.

## Tests
- Every rule and formula has unit tests, including edge cases (missing data, ties, empty catalogue, stale source).
- API tests with `TestClient` checking response shapes. Tests never call paid or network services: use fixtures and fakes.
- Tests are readable specifications: test names state the rule (`test_scenario_never_lowers_essential_levels`).

## Commits
- Conventional style: `evidence: …`, `match: …`, `api: …`, `web: …`, `data: …`, `test: …`, `docs: …`, `chore: …`. One logical change per commit. The body explains *why* when it isn't obvious.

## Before finishing any task
- Re-read the diff as a reviewer: is anything unclear, duplicated, over-engineered or untested? Simplify.
- Update the module's explanation doc (qart-explain skill) if behaviour changed.
