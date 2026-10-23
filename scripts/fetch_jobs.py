"""Fetch the public ATS job boards and refresh data/snapshots/ats_signals.json.

    python scripts/fetch_jobs.py           # one ingestion run (about a minute, ~30 requests)
    python scripts/fetch_jobs.py --check   # only verify the board tokens, write nothing
    python scripts/fetch_jobs.py --retag   # re-tag stored jobs from saved raw files (no network)

Schedule it daily (the history is built from daily snapshots): .github/workflows/refresh-jobs.yml
runs it every day and opens one pull request with the updated snapshot.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.jobs.config import SOURCES, default_ats_config, load_companies  # noqa: E402
from src.jobs.pipeline import DB_PATH, RAW_DIR, build_snapshot, retag, run  # noqa: E402
from src.jobs.sources import fetchers  # noqa: E402
from src.signals.pipeline import SNAPSHOT_DIR, write_atomic  # noqa: E402


def check() -> int:
    cfg, bad = default_ats_config(), 0
    with httpx.Client(headers={"User-Agent": cfg.http.user_agent}) as client:
        by_source = fetchers(cfg.http.politeness, lambda s: None, cfg.http.lever_page_size)
        for source in SOURCES:
            for c in load_companies()[source]:
                try:
                    _, postings = by_source[source].fetch(client, c.token, c.name)
                    print(f"ok   {source:10} {c.token:20} {len(postings):5} open jobs")
                except httpx.HTTPError as exc:
                    bad += 1
                    print(f"FAIL {source:10} {c.token:20} {exc}")
    return 1 if bad else 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if "--check" in sys.argv:
        sys.exit(check())
    if "--retag" in sys.argv:
        cfg = default_ats_config()
        print(f"re-tagged {retag(RAW_DIR, DB_PATH, cfg)} postings")
        snapshot = build_snapshot(DB_PATH, cfg, datetime.now(UTC).isoformat(timespec="seconds"))
        if snapshot:
            write_atomic(SNAPSHOT_DIR / cfg.snapshot_name, snapshot)
            print("snapshot rebuilt")
        sys.exit(0)
    print(json.dumps(run(), indent=2))
