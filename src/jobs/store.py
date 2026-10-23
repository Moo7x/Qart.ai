"""SQLite store of normalised postings across runs (standard library only).

Deduplicated by (source, job_id). Each run upserts what the boards list today: a new job gets
first_seen = last_seen = run date, a job seen again keeps first_seen and moves last_seen. A job
missing from a run is not deleted; its last_seen simply stops moving, which is how a closed
posting shows up. Each company fetch is logged in `runs` (ok, jobs found, error). The file lives
in the gitignored data/raw/ats/ (job descriptions are never committed); CI keeps it in a cache.
"""

import json
import sqlite3
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from src.jobs.sources import Posting
from src.jobs.tagging import Tags

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
  source TEXT NOT NULL, job_id TEXT NOT NULL, company TEXT NOT NULL, title TEXT NOT NULL,
  department TEXT, location TEXT NOT NULL, remote INTEGER NOT NULL, employment_type TEXT,
  posted_at TEXT, url TEXT NOT NULL, description TEXT NOT NULL,
  regions TEXT NOT NULL, family TEXT, mentions_ai INTEGER NOT NULL, skills TEXT NOT NULL,
  first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
  PRIMARY KEY (source, job_id)
);
CREATE TABLE IF NOT EXISTS runs (
  run_date TEXT NOT NULL, source TEXT NOT NULL, company TEXT NOT NULL,
  ok INTEGER NOT NULL, jobs INTEGER NOT NULL, error TEXT,
  PRIMARY KEY (run_date, source, company)
);
"""


@dataclass(frozen=True)
class StoredJob:
    source: str
    job_id: str
    company: str
    title: str
    regions: tuple[str, ...]
    family: str | None
    mentions_ai: bool
    skills: tuple[str, ...]
    first_seen: str
    last_seen: str


@contextmanager
def connect(path: Path) -> Iterator[sqlite3.Connection]:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def upsert(
    conn: sqlite3.Connection, run_date: str, postings: Iterable[tuple[Posting, Tags]]
) -> int:
    rows = [
        (
            p.source,
            p.job_id,
            p.company,
            p.title,
            p.department,
            p.location,
            int(p.remote),
            p.employment_type,
            p.posted_at,
            p.url,
            p.description,
            json.dumps(t.regions),
            t.family,
            int(t.mentions_ai),
            json.dumps(t.skills),
            run_date,
            run_date,
        )
        for p, t in postings
    ]
    conn.executemany(
        """INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
           ON CONFLICT (source, job_id) DO UPDATE SET
             company=excluded.company, title=excluded.title, department=excluded.department,
             location=excluded.location, remote=excluded.remote,
             employment_type=excluded.employment_type, posted_at=excluded.posted_at,
             url=excluded.url, description=excluded.description, regions=excluded.regions,
             family=excluded.family, mentions_ai=excluded.mentions_ai, skills=excluded.skills,
             first_seen=MIN(jobs.first_seen, excluded.first_seen),
             last_seen=MAX(jobs.last_seen, excluded.last_seen)""",
        rows,
    )
    return len(rows)


def log_run(
    conn: sqlite3.Connection,
    run_date: str,
    source: str,
    company: str,
    ok: bool,
    jobs: int,
    error: str | None,
) -> None:
    conn.execute(
        "INSERT OR REPLACE INTO runs VALUES (?,?,?,?,?,?)",
        (run_date, source, company, int(ok), jobs, error),
    )


def all_jobs(conn: sqlite3.Connection) -> list[StoredJob]:
    cur = conn.execute(
        "SELECT source, job_id, company, title, regions, family, mentions_ai, skills, "
        "first_seen, last_seen FROM jobs"
    )
    return [
        StoredJob(s, j, c, t, tuple(json.loads(r)), f, bool(ai), tuple(json.loads(sk)), fs, ls)
        for s, j, c, t, r, f, ai, sk, fs, ls in cur.fetchall()
    ]


def run_dates(conn: sqlite3.Connection) -> list[str]:
    return [
        r[0]
        for r in conn.execute("SELECT DISTINCT run_date FROM runs WHERE ok = 1 ORDER BY run_date")
    ]


def last_run(conn: sqlite3.Connection) -> list[dict[str, object]]:
    cur = conn.execute(
        "SELECT source, company, ok, jobs, error FROM runs "
        "WHERE run_date = (SELECT MAX(run_date) FROM runs) ORDER BY source, company"
    )
    return [
        {"source": s, "company": c, "ok": bool(ok), "jobs": n, "error": e}
        for s, c, ok, n, e in cur.fetchall()
    ]
