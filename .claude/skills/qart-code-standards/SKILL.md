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
- Frontend: TypeScript `strict: true`, ESLint + Prettier.
- Before each commit: `ruff format . && ruff check . && mypy src && pytest -q` (frontend: `npm run lint && npm run typecheck && npm test`). Don't commit red.
- A pre-commit hook (`pre-commit` with ruff + a secret scanner such as gitleaks) if available.

## Structure
- One responsibility per module. Engine logic in `src/engine/` is **pure functions** (no FastAPI, no DB, no network), so it is testable and explainable. Routes in `src/api_*.py` only validate, call the engine, and return contract models. Persistence only in `src/store.py`.
- Contract objects are **Pydantic models** in one place (`src/engine/models.py` or `src/contract.py`), mirroring `schemas/examples/`.
- No hidden state: pass inputs explicitly, return outputs explicitly.

## Style
- Full type hints on every function. Small functions (aim for ≤40 lines). Descriptive names (`independent_success_count`, not `isc`).
- **No magic numbers.** Every weight, threshold and parameter lives in a named constant or config file (e.g. `src/engine/params.py`) with a comment: what it is, why this value, and whether it is an *assumption*, *declared parameter* or *derived from a source*.
- Docstrings (Google style) on public functions: purpose, args, returns, and for formulas the formula itself in plain text.
- Comments explain **why**, not what.
- Errors: raise specific exceptions in the engine; routes translate them to clear HTTP errors (`422` bad input, `404` unknown id). Never swallow exceptions silently.
- Logging via `logging` (no prints) with meaningful messages. Never log secrets or personal data.
- No dead code, no commented-out blocks, no unused imports, no TODOs without an owner and a reason.

## Tests
- Every engine rule and formula has unit tests, including edge cases (zero events, flagged events, ties, empty catalogue).
- Golden-journey sequence tests for the evidence rules and recommendations.
- API tests with `httpx`/`TestClient` checking contract shapes.
- Tests are readable specifications: test names state the rule (`test_checkin_success_gives_one_of_two_independent`).

## Commits
- Conventional style: `engine: …`, `api: …`, `data: …`, `test: …`, `docs: …`, `chore: …`. One logical change per commit. The body explains *why* when it isn't obvious.

## Before finishing any task
- Re-read the diff as a reviewer: is anything unclear, duplicated, over-engineered or untested? Simplify.
- Update the module's explanation doc (qart-explain skill) if behaviour changed.
