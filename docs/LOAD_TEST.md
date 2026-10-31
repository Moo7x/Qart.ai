# Load test

`scripts/load/locustfile.py`: virtual people create a synthetic profile, then open matches, the
plan, the tracks, the trends, the forecast and the status (5% also read a sample CV, capped).

## Local run, 2026-11-01 (one uvicorn process, SQLite, a Windows laptop)

| Run | Requests | Failures | Median | 95th percentile |
|---|---|---|---|---|
| 25 people, 60 s, before the fix | 174 | 16 (9%) | 4.4 s | 12 s |
| 50 people, 60 s, before the fix | 197 | 24 (12%) | 9.3 s | 31 s |
| 25 people, 60 s, after the fix | 261 | 0 | 2.8 s | 8.4 s |

**What failed and what changed.** The failures were SQLite "database is locked" errors when
several people saved at once (local only: the deployed app uses Postgres); SQLite now waits up to
30 s for a writer. Ranking recomputed the industry forecast on every call; it is now cached per
evidence snapshot, task-model version and scenario.

**What this shows and what it does not.** One local process is the slowest setting: every request
waits for the one before it. The deployed app runs on Replit Autoscale with Postgres and can add
instances; a run against it (command in the locustfile) is still to be done and must not overlap
a judging session. The slowest step is creating a profile (median 5.6 s), which ranks every role
and plans the best one before answering.
