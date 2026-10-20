---
name: qart-golden-journey
description: Run the Qart.ai golden-journey acceptance test (contract §6) against a local or Replit deployment and report pass/fail per step. Use at checkpoints C1/M1/C2/M2, after merging, and before recording the demo video.
---

# Qart.ai golden-journey test

Target: the base URL the human gives (local `http://localhost:8000` or the Replit deployment URL). Prefer the **deployment URL** at merge points.

## Steps to verify (from team/00_SHARED_CONTRACT.md §6)
1. **Profile:** `GET /api/skills/u_aina` returns states for the 8 practised skills; the intake self-rating for `unsupported_adjustment` = 8/10.
2. **case_003:** post a session where the decision is `sign_off` → the grader marks it incorrect → companion messages walk up the help ladder (`help_level` increases one step per "stuck" request; **no answer rows revealed before the allowed level**) → final event shows "missed, then found with hint" (`help_level_max` = 2).
3. **Targeted next case:** `GET /api/next-case/u_aina` returns case_006 (or another case containing `unsupported_adjustment`) with a `because` that mentions case_003.
4. **Check-in:** a correct independent decision on checkin_001 → SkillState for `unsupported_adjustment` = `observed_with_help`, `independent_successes` = 1, and `why` says one more independent success in a later session is needed. **It must NOT say demonstrated yet.**
5. **Path revised:** `GET /api/path/u_aina` now contains a confirmation check-in instead of the adjustments learning module; the recommendation's `changed_since` points to her events.
6. **Updated external evidence (M2):** ingest the newer snapshot → `GET /api/snapshots/diff` shows signal changes + `suggested_assumption_reviews` → `PUT /api/assumptions` (approve) bumps the version → recommendation `requirement_card` and ranking change, labelled "historical data replay".
7. **Trust checks (M2):** clean case_001 → `sign_off` graded correct; AI-false-alarm case_007 → `sign_off` graded correct.

## How
- Use plain HTTP calls (curl/httpx) for the API steps. If the Playwright MCP is available, also click through the UI for steps 2, 4 and 5 and save screenshots to `docs/screenshots/` (useful for the deck).
- Use a fresh demo user or reset the demo state first (`POST /api/demo/reset` if it exists). Don't pollute real demo data.
- Output: a table step · pass/fail · evidence (response snippet or screenshot path) · fix suggestion. Also note the URL tested and the time (MYT).
