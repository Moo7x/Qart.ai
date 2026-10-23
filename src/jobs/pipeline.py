"""One ingestion run: fetch every configured board, save the raw responses as a dated snapshot,
tag and upsert the postings, then write data/snapshots/ats_signals.json for the app.

Per company: a wrong token or a failing board is logged and skipped; the run continues. A run in
which no company succeeds writes nothing, so the previous snapshot stays. The app reads only the
committed aggregate snapshot (counts and shares, no job descriptions).
"""

import json
import logging
import time
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import httpx

from src.engine.catalogue import REPO_ROOT, default_catalogue
from src.jobs import metrics
from src.jobs.config import SOURCES, AtsConfig, Company, default_ats_config, load_companies
from src.jobs.sources import Posting, fetchers
from src.jobs.store import all_jobs, connect, last_run, log_run, run_dates, upsert
from src.jobs.tagging import Tagger, Tags, strip_boilerplate
from src.signals.config import default_config
from src.signals.pipeline import SNAPSHOT_DIR, write_atomic

logger = logging.getLogger(__name__)
RAW_DIR = REPO_ROOT / "data" / "raw" / "ats"
DB_PATH = RAW_DIR / "jobs.sqlite"
REGIONS = ("global", "malaysia", "singapore", "malaysia_singapore", "apac", "remote")
ENDPOINTS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true",
    "lever": "https://api.lever.co/v0/postings/{token}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true",
}
CAVEATS = [
    "Open postings from the public job boards of the companies listed (Greenhouse, Lever, "
    "Ashby): a sample biased toward tech and fast-growing firms that use these systems, not the "
    "whole market.",
    "The boards list only jobs open today, so history starts with the first snapshot and is built "
    "by recording when each job first and last appeared.",
    "AI mentions and skills are matched by declared keyword patterns, not read by a person.",
    "Shares from fewer than {min_sample} postings are shown as insufficient data.",
]


def tag_company(
    postings: list[Posting], tagger: Tagger, cfg: AtsConfig
) -> list[tuple[Posting, Tags]]:
    """Remove the company's boilerplate, then tag each posting (the same steps for retagging)."""
    bp = cfg.boilerplate
    cleaned = strip_boilerplate(postings, bp.min_share, bp.min_postings, bp.shingle_words)
    return [(p, tagger.tag(p)) for p in cleaned]


def retag(raw_dir: Path, db_path: Path, cfg: AtsConfig) -> int:
    """Rebuild every stored posting's tags from the saved raw responses (no network), e.g. after
    a rule change in ats_config.json. first_seen / last_seen are kept."""
    tagger = Tagger(cfg, default_config().skills)
    by_source = fetchers(cfg.http.politeness, lambda s: None, cfg.http.lever_page_size)
    names = {c.token: c.name for cs in load_companies().values() for c in cs}
    count = 0
    with connect(db_path) as conn:
        for day_dir in sorted(d for d in raw_dir.iterdir() if d.is_dir()):
            for path in sorted(day_dir.glob("*__*.json")):
                source, token = path.stem.split("__", 1)
                raw = json.loads(path.read_text(encoding="utf-8"))
                jobs = raw if source == "lever" else raw.get("jobs", [])
                jobs = [j for j in jobs if j.get("isListed", True)]
                fetcher = by_source[source]
                postings = [fetcher.normalise(j, names.get(token, token)) for j in jobs]
                count += upsert(conn, day_dir.name, tag_company(postings, tagger, cfg))
    return count


def ingest(
    run_date: str,
    db_path: Path,
    raw_dir: Path,
    companies: dict[str, list[Company]],
    cfg: AtsConfig,
    client: httpx.Client,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    """Fetch, save raw, tag and upsert. Returns a per-run summary."""
    tagger = Tagger(cfg, default_config().skills)
    by_source = fetchers(cfg.http.politeness, sleep, cfg.http.lever_page_size)
    day_dir = raw_dir / run_date
    day_dir.mkdir(parents=True, exist_ok=True)
    summary: dict[str, Any] = {
        "run_date": run_date,
        "companies_ok": 0,
        "companies_failed": 0,
        "jobs": 0,
        "errors": [],
    }
    with connect(db_path) as conn:
        for source in SOURCES:
            for company in companies.get(source, []):
                try:
                    raw, postings = by_source[source].fetch(client, company.token, company.name)
                except (httpx.HTTPError, ValueError) as exc:
                    error = f"{type(exc).__name__}: {exc}"[:300]
                    logger.warning("%s/%s skipped: %s", source, company.token, error)
                    log_run(conn, run_date, source, company.name, False, 0, error)
                    summary["companies_failed"] += 1
                    summary["errors"].append(f"{source}/{company.token}: {error}")
                    continue
                (day_dir / f"{source}__{company.token}.json").write_text(
                    json.dumps(raw), encoding="utf-8"
                )
                upsert(conn, run_date, tag_company(postings, tagger, cfg))
                log_run(conn, run_date, source, company.name, True, len(postings), None)
                summary["companies_ok"] += 1
                summary["jobs"] += len(postings)
    logger.info(
        "ATS run %s: %s companies ok, %s failed, %s open jobs",
        run_date,
        summary["companies_ok"],
        summary["companies_failed"],
        summary["jobs"],
    )
    return summary


def build_snapshot(db_path: Path, cfg: AtsConfig, fetched_at: str) -> dict[str, Any] | None:
    """The app-facing aggregate (no descriptions); None when no run has succeeded yet."""
    with connect(db_path) as conn:
        jobs, dates, runs = all_jobs(conn), run_dates(conn), last_run(conn)
    if not dates:
        return None
    first, last = date.fromisoformat(dates[0]), date.fromisoformat(dates[-1])
    vocabulary = default_catalogue().vocabulary
    skill_names = {k: (s.market_name or s.name) for k, s in vocabulary.items() if s.trend_tracked}
    skills, families = metrics.latest_breakdowns(jobs, REGIONS, skill_names, last, cfg.min_sample)
    return {
        "source": "Public ATS job boards (Greenhouse, Lever, Ashby)",
        "source_url": "catalogue/ats_companies.json",
        "endpoints": ENDPOINTS,
        "license": "Public job-board APIs (no key); posting text © each employer; "
        "only counts are stored here",
        "attribution": "Source: public job boards of the companies listed "
        "(Greenhouse, Lever, Ashby)",
        "update_frequency": "daily snapshot (GitHub Actions)",
        "data_as_of": last.isoformat(),
        "first_snapshot": first.isoformat(),
        "snapshots": len(dates),
        "fetched_at": fetched_at,
        "caveats": [c.format(min_sample=cfg.min_sample) for c in CAVEATS],
        "min_sample": cfg.min_sample,
        "min_periods_for_chart": cfg.min_periods_for_chart,
        "regions": [{"id": r, "label": cfg.region_labels[r]} for r in REGIONS],
        "coverage": {
            "companies": sorted({r["company"] for r in runs if r["ok"]}),
            "companies_failed": [f"{r['source']}/{r['company']}" for r in runs if not r["ok"]],
            "open_jobs_latest_run": sum(int(r["jobs"]) for r in runs if r["ok"]),  # type: ignore[call-overload]
            "jobs_ever_seen": len(jobs),
        },
        "series": metrics.ai_series(jobs, REGIONS, first, last, "week", cfg.min_sample)
        + metrics.ai_series(jobs, REGIONS, first, last, "month", cfg.min_sample),
        "skills_latest_week": skills,
        "families_latest_week": families,
    }


def run(
    now: datetime | None = None,
    db_path: Path = DB_PATH,
    raw_dir: Path = RAW_DIR,
    out_dir: Path = SNAPSHOT_DIR,
    companies: dict[str, list[Company]] | None = None,
    cfg: AtsConfig | None = None,
    make_client: Callable[[], httpx.Client] | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[str, Any]:
    cfg = cfg or default_ats_config()
    now = now or datetime.now(UTC)
    make_client = make_client or (lambda: httpx.Client(headers={"User-Agent": cfg.http.user_agent}))
    with make_client() as client:
        summary = ingest(
            now.date().isoformat(),
            db_path,
            raw_dir,
            companies or load_companies(),
            cfg,
            client,
            sleep,
        )
    if summary["companies_ok"] == 0:
        summary["snapshot"] = "kept previous: no company fetched"
        return summary
    snapshot = build_snapshot(db_path, cfg, now.isoformat(timespec="seconds"))
    if snapshot is not None:
        write_atomic(out_dir / cfg.snapshot_name, snapshot)
        summary["snapshot"] = "ok"
    return summary
