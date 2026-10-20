---
name: qart-contract-check
description: Check that Qart.ai JSON outputs, API responses and UI text follow the shared contract (team/00_SHARED_CONTRACT.md) and the hackathon rules. Use before every commit that touches schemas, endpoints, events, recommendations or UI copy, and before merge points.
---

# Qart.ai contract check

Run this whenever code produces or consumes contract objects (Profile, Case, Event, SkillState, Role, Snapshot, CompanyAssumptions, Recommendation, PathPlan, Course, OptimizerProposal).

## Steps
1. Read `team/00_SHARED_CONTRACT.md` (§3 vocabulary, §4 objects, §5 endpoints) and the examples in `schemas/examples/`.
2. For each changed endpoint or object:
   - Field names and types match the example exactly (no renamed or extra required fields).
   - Enum values come from §3 (help_level 0–4, decision, skill state, scenario, case mode, cause_if_wrong).
   - Skill IDs exist in `catalogue/skills.json`.
3. Rule checks (fail the check if any is violated):
   - **No mastery percentages** in any user-facing field or UI string. SkillState shows `state`, `why` and `evidence_trail`. `provisional_estimate` is internal only.
   - Every recommendation, role, course and statistic shown to users has a **source** (label + URL) and, for data, a **date**.
   - Numbers are labelled as **evidence** (dated source), **assumption** (company layer B or a declared parameter) or **synthetic**.
   - `GET /api/cases/{id}` never returns `ground_truth`. Only `src/companion/grader.py` reads it.
   - HR endpoints return aggregates only (groups under 5 suppressed), with no names.
   - Recommendation `formula` is `0.55*coverage + 0.20*confidence + 0.10*interest - 0.15*effort` (effort is a penalty), unless the contract version changed.
   - The optimiser only writes to `src/companion/playbooks/candidates/` and never reads `eval/acceptance/`.
   - No secrets in code: search for `sk-`, `api_key=`, `Bearer `, `.env` contents.
4. Report a short table: object/endpoint · status · problem · suggested fix. If the contract itself must change, **stop and tell the human**. Contract changes need both teammates and a version bump.
