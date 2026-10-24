# Local baseline verification — 23 October 2026

Evidence of the current build, not a claim that the cloud deployment or career outcomes are proven.

| Domain 1 requirement | Implemented and checked locally | Material limit |
|---|---|---|
| Profile intake | Manual six-question working-adult and graduate flows, profile creation, reload; PDF/DOCX/text and quoted-CV validation have offline tests | No real CVs. This continuation made no paid model calls; Claude previously checked real gpt-4o-mini intake. |
| Updatable signal layer | Seven collectors (OpenDOSM, DOSM job ads, Economic Index occupations and linked O*NET tasks, TalentCorp, O*NET 31.0, ILO exposure index, MyCOL 2024/2025), saved source/date/passage, immutable revisions, run lock, retries, no-change behaviour; a backtest version is stored whenever trend data changes; real stored data shown in browser | Independent deployed schedule not verified. DOSM broad groups are context, not individual skill demand. ILO exposure is an occupation-level estimate of potential. |
| Explainable future roles | All nine destinations scored; exact requirement contributions, essential gaps, scenario switch and destination choice checked in browser; each role shows its O*NET tasks with observed AI use, ILO exposure and TalentCorp impact kept apart, a demand outlook (DOSM, TalentCorp, MyCOL) and an optional gpt-4o-mini explanation whose sentences cite computed facts and contain no numbers; Overview shows a personal skills radar | Fit uses claimed levels and declared weights; it is not hiring probability or validated proficiency. The task crosswalk (68 links) is a declared mapping; 21 of 61 requirements have no fitting O*NET task and use the occupation figure. Reported deployment is not collected yet. |
| Personal pathways | Thirty linked resources, prerequisite ordering, weekly-hours scheduling, uncovered gaps and goal persistence; browser and offline tests | Greedy baseline, not a proven optimum. Course gains are hypothetical. Ten required skills have no verified free resource. |
| SDG mapping | Roles/skills/steps carry target and contribution mechanisms; pack/API checks and pathway/future UI | These mechanisms do not measure achieved SDG impact. |
| Uncertainty | Moderate/fast scenarios with fixed essential levels and weights; observed versus assumption labels; scenario shifts use task-level AI use where published | The AI-use-to-emphasis transfer is a declared scenario rule, not a learned Malaysian adoption forecast. |
| Fairness | `tests/test_fairness.py`: three synthetic CVs differing only in protected attributes give identical scrubbed text, model input, fallback extraction, ranks, gaps and pathways | Protected facts written inside sentences are not removed. |

## Success test and change behaviour

- Manual intake → ranked roles → chosen destination → pathway → future comparison works against
  the real local API. Reload preserves the synthetic profile and scenario.
- In two profiles selecting the same destination, marking one course done in the first leaves
  the second at 0/12. Completion does not change skills or scores.
- At a 390×844 browser viewport, Future and What changed had no document-level horizontal overflow.
- Real stored AEI Apr→May replay showed a synthetic reporting-level-2 graduate's fast-scenario
  Procurement Analyst fit moving 8.4→8.3. Exact weight/contribution deltas and source rows are shown;
  the Finance Systems pathway stayed unchanged. This is not two separate publication vintages.
- Offline integration tests show a schedule-triggered collector run publishing proposals without
  any page request; accept/decline, cross-profile access, stale proposals, unchanged values, revision
  cutoffs and read-only replay are checked. No test calls paid/network services.
- `tests/test_acceptance_mechanism.py` (acceptance check 10): one scheduled finding on one O*NET
  task changes profile A's dashboard weight, fit and proposal, and changes nothing in profile B's
  chosen role, whose skills link to no task the finding concerns.
- A disposable real local PostgreSQL check verified proposal persistence, unchanged accepted
  results before acceptance, acceptance and replay. It used synthetic inputs, not production data.

## Deployment verification still required

The team pushes and deploys. Keep the web/API deployment separate from an independent scheduled
pipeline run using the same persistent Postgres database. Run command on Replit (the start
script's virtual environment): `.venv/bin/python -m src.pipeline.run --trigger schedule`. Replit's Scheduled deployment runs a command and
stops; it does not serve the website. Configure a daily schedule/time zone and a timeout sufficient
for first ingestion, then retain a schedule-triggered run log from an interval with no browser visits.
Source cadence remains quarterly/annual/irregular even if checked daily.

Verify the deployed journey, refresh/restart persistence, admin-token protection and no-change run
before claiming production readiness. App-open catch-up is a backup, not proof of autonomous updates.
Current platform reference: [Replit deployment types](https://docs.replit.com/features/publishing/deployment-types).
