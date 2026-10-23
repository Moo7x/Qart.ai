# Architecture

Registered public sources → collectors → immutable observations → measures and labelled signals
→ declared scenario emphasis → person-level fit/gaps → chosen destination → ordered pathway.
Source refresh → stored comparison/proposal → user accepts or declines → accepted journey.

- `src/collectors/`, `src/evidence/`, `src/pipeline/`: four collectors, SQLite/Postgres evidence,
  deduplication/revisions, historical measures/backtest, locks, retries and run history. Independent
  scheduled deployment runs without visitors; stale-on-visit catch-up is only a backup.
- `src/pack.py`, `data/packs/gbs_fa/`: 46 skills, 11 starting roles, 9 destinations, 30 linked
  resources, prerequisite relationships and SDG mechanisms. Numerical levels are declared policy.
- `src/intake/`: synthetic PDF/DOCX/text or questionnaire, identifier scrubbing, quoted claims,
  gpt-4o-mini or labelled keyword/form fallback; RunPod/BM25 skill discovery.
- `src/match/`, `src/pathway/`: pure functions; every score component and hypothetical course
  gain is explained. Source observations do not establish a person's proficiency.
- `src/journey/store.py`: claimed profile and selected destination behind a random browser-held
  profile key. `src/changes/`: accepted evidence cutoffs, pure before/after calculations,
  persisted proposals, stale-update checks and read-only source-period replay.
- `src/api/`: HTTP validation, pure computation and persistence. `web/src/`: onboarding,
  evidence, role explanations, pathway, future comparison and What changed.

The LLM never writes scores. Checkboxes track learning progress, not mastery. No real CVs,
payments, hiring decisions, recruitment integrations or practice tutoring. HR, Telegram,
what-if/robust planning and the research agent are deferred; voice and on-screen agent are on hold.
See [evidence](evidence.md), [journey](journey.md) and [changes](changes.md) for formulas and limits.
