# Local baseline verification — 23 October 2026

Evidence of the current build, not a claim that the cloud deployment or career outcomes are proven.

| Domain 1 requirement | Implemented and checked locally | Material limit |
|---|---|---|
| Profile intake | Manual six-question working-adult and graduate flows, profile creation, reload; PDF/DOCX/text and quoted-CV validation have offline tests | No real CVs. This continuation made no paid model calls; Claude previously checked real gpt-4o-mini intake. |
| Updatable signal layer | Four collectors, saved source/date/passage, immutable revisions, run lock, retries, no-change behaviour; real stored data shown in browser | Independent deployed schedule not verified. DOSM broad groups are context, not individual skill demand. |
| Explainable future roles | All nine destinations scored; exact requirement contributions, essential gaps, scenario switch and destination choice checked in browser | Fit uses claimed levels and declared weights; it is not hiring probability or validated proficiency. |
| Personal pathways | Thirty linked resources, prerequisite ordering, weekly-hours scheduling, uncovered gaps and goal persistence; browser and offline tests | Greedy baseline, not a proven optimum. Course gains are hypothetical. Ten required skills have no verified free resource. |
| SDG mapping | Roles/skills/steps carry target and contribution mechanisms; pack/API checks and pathway/future UI | These mechanisms do not measure achieved SDG impact. |
| Uncertainty | Moderate/fast scenarios with fixed essential levels and weights; observed versus assumption labels | The AI-use-to-emphasis transfer is a declared scenario rule, not a learned Malaysian adoption forecast. |

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
- A disposable real local PostgreSQL check verified proposal persistence, unchanged accepted
  results before acceptance, acceptance and replay. It used synthetic inputs, not production data.

## Deployment verification still required

The team pushes and deploys. Keep the web/API deployment separate from an independent scheduled
pipeline run using the same persistent Postgres database. Run command:
`python -m src.pipeline.run --trigger schedule`. Replit's Scheduled deployment runs a command and
stops; it does not serve the website. Configure a daily schedule/time zone and a timeout sufficient
for first ingestion, then retain a schedule-triggered run log from an interval with no browser visits.
Source cadence remains quarterly/annual/irregular even if checked daily.

Verify the deployed journey, refresh/restart persistence, admin-token protection and no-change run
before claiming production readiness. App-open catch-up is a backup, not proof of autonomous updates.
Current platform reference: [Replit deployment types](https://docs.replit.com/features/publishing/deployment-types).
