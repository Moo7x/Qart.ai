---
name: qart-git-workflow
description: Git commit and push discipline for Qart.ai so the repository shows a genuine, continuous, readable history (the hackathon reviews commit history and flags large last-minute commits). Use before every commit, before pushing, and when merging branches at checkpoints.
---

# Qart.ai git workflow

The organisers can inspect commit history. *"One giant last-minute commit gets reviewed."* A near-complete codebase in one commit may lead to disqualification. **History is built by commits; pushing later keeps their timestamps.**

## Commit rules
- **One logical change per commit**, roughly one task sub-step (e.g. "evidence-state rules + tests"). Aim for **under ~300 changed lines** of hand-written code. Generated or data files go in their own commits.
- Commit **as soon as a sub-step works and checks pass**, not at the end of a session.
- Message format: `<area>: <what changed>` (areas: `engine`, `api`, `data`, `catalogue`, `eval`, `web`, `companion`, `cases`, `test`, `docs`, `chore`). Imperative, ≤72 characters. Add a body explaining *why* when not obvious.
  - Good: `engine: add help-weighted evidence states with golden-journey tests`
  - Bad: `update`, `fix stuff`, `WIP`, `final`
- Before each commit:
  1. `git status`: nothing unintended. **Never** `data/raw/`, `.env`, keys, `*.sqlite`, `node_modules/`, `web/dist/`.
  2. Checks pass (ruff, mypy, pytest; or lint, typecheck and tests for web).
  3. Stage explicitly (`git add <paths>`) rather than `git add -A` when unrelated files changed.
- Never rewrite published history: **no `git push --force`, no squashing, no rebasing shared branches, no amending pushed commits.**
- Don't change git identity or config.

## Branches
- `main` = integrated, working state. `a/engine` = Person A. `b/app` = Person B.
- Merge into `main` only at checkpoints (M1, M2), via a pull request or `git merge --no-ff` so the branch history stays visible. **Don't squash-merge.**
- After a merge, both pull `main` and continue on their own branch (`git merge main` into it).

## Pushing (once the GitHub remote exists)
- Push your branch **at least 2–3 times a day** and after every increment: `git push origin <branch>`.
- Optionally tag finished increments on `main`: `inc0-base`, `inc1-golden-journey`, `inc2-evidence-recompute`, `inc3-trust`.
- Before the deadline: push everything, make the repo public, and add the committee collaborators. **After the deadline: no more pushes** (repository freeze) unless the organisers allow it.

## If you are an agent working without a remote
- Keep committing locally per the rules above. Do not create remotes or push unless the human asks.
