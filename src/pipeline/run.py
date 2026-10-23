"""Run every registered collector once, store new observations and log the run.

Run it on a schedule (Replit Scheduled Deployment) or from the admin "Run now" button:

    python -m src.pipeline.run --trigger schedule

A database lock stops two runs overlapping. Each source gets a bounded number of attempts; a source
that keeps failing is logged as failed and the others still run, so one outage never blocks the
rest. A run that finds nothing new is logged as "no change", which is a normal, honest result.
"""

import argparse
import logging
import threading
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import Engine

from src import params
from src.changes.service import refresh_proposals
from src.collectors import aei, dosm_jmi, dosm_wages, ilo, mycol, onet, talentcorp
from src.collectors.base import Collect
from src.evidence.registry import registry
from src.evidence.store import (
    DbSourceState,
    acquire_lock,
    finish_run,
    insert_observations,
    latest_observation_id,
    list_runs,
    release_lock,
    start_run,
)

logger = logging.getLogger(__name__)

LOCK_NAME = "pipeline"
LOCK_TTL = timedelta(minutes=30)  # longer than a full run (the 220 MB Economic Index file included)
MAX_ATTEMPTS = 2  # one retry: covers a dropped connection without hammering a source that is down
RETRY_PAUSE_SECONDS = 3.0
HTTP_TIMEOUT = httpx.Timeout(60.0, connect=15.0)

COLLECTORS: Mapping[str, Collect] = {
    "dosm_wages": dosm_wages.collect,
    "dosm_jmi": dosm_jmi.collect,
    "aei": aei.collect,
    "talentcorp": talentcorp.collect,
    "onet": onet.collect,
    "ilo": ilo.collect,
    "mycol": mycol.collect,
}


@dataclass
class RunSummary:
    run_id: int | None
    status: str  # "changed" | "no change" | "partial" | "failed" | "skipped: locked"
    new_observations: int = 0
    sources: list[dict[str, Any]] = field(default_factory=list)


def _run_source(
    engine: Engine,
    client: httpx.Client,
    source_id: str,
    collect: Collect,
    run_id: int,
    pause: float,
) -> dict[str, Any]:
    error = ""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        state = DbSourceState(engine, source_id)
        started = time.monotonic()
        try:
            result = collect(client, state)
            new = insert_observations(engine, result.observations, run_id)
            state.commit()
            return {
                "source_id": source_id,
                "status": "ok",
                "fetched": len(result.observations),
                "new": new,
                "note": result.note,
                "attempts": attempt,
                "seconds": round(time.monotonic() - started, 1),
            }
        except Exception as exc:  # noqa: BLE001
            # Isolation boundary: whatever one source raises (network, parsing, a database
            # constraint), it is logged as that source's failure and the other sources still run.
            error = f"{type(exc).__name__}: {exc}"
            logger.warning("source %s attempt %d failed: %s", source_id, attempt, error)
            if attempt < MAX_ATTEMPTS:
                time.sleep(pause)
    return {
        "source_id": source_id,
        "status": "failed",
        "fetched": 0,
        "new": 0,
        "note": "kept the last good data",
        "error": error[:300],
        "attempts": MAX_ATTEMPTS,
    }


def overall_status(results: list[dict[str, Any]]) -> str:
    failed = sum(r["status"] == "failed" for r in results)
    if results and failed == len(results):
        return "failed"
    if failed:
        return "partial"
    return "changed" if any(r["new"] for r in results) else "no change"


def run_pipeline(
    engine: Engine,
    trigger: str,
    client_factory: Callable[[], httpx.Client] | None = None,
    retry_pause: float = RETRY_PAUSE_SECONDS,
) -> RunSummary:
    holder = uuid.uuid4().hex
    if not acquire_lock(engine, LOCK_NAME, holder, LOCK_TTL):
        return RunSummary(run_id=None, status="skipped: locked")
    try:
        run_id = start_run(engine, trigger)
        try:
            return _run_all(engine, run_id, client_factory, retry_pause)
        except Exception as exc:
            # A run must never stay "running": record the failure, then let the error surface.
            finish_run(
                engine,
                run_id,
                "failed",
                0,
                [
                    {
                        "source_id": "pipeline",
                        "status": "failed",
                        "fetched": 0,
                        "new": 0,
                        "error": f"{type(exc).__name__}: {exc}"[:300],
                    }
                ],
            )
            raise
    finally:
        release_lock(engine, LOCK_NAME, holder)


def _run_all(
    engine: Engine,
    run_id: int,
    client_factory: Callable[[], httpx.Client] | None,
    retry_pause: float,
) -> RunSummary:
    previous_cutoff = latest_observation_id(engine)
    factory = client_factory or (lambda: httpx.Client(timeout=HTTP_TIMEOUT))
    results: list[dict[str, Any]] = []
    with factory() as client:
        for source in registry().values():
            collect = COLLECTORS.get(source.collector)
            if collect is None:
                results.append(
                    {
                        "source_id": source.id,
                        "status": "failed",
                        "fetched": 0,
                        "new": 0,
                        "error": f"no collector named {source.collector}",
                    }
                )
                continue
            results.append(_run_source(engine, client, source.id, collect, run_id, retry_pause))
    status = overall_status(results)
    new_total = sum(r["new"] for r in results)
    # Also retry publication after a previous run stored evidence but failed before publication.
    refresh_proposals(engine, previous_cutoff, run_id)
    finish_run(engine, run_id, status, new_total, results)
    return RunSummary(run_id, status, new_total, results)


def is_stale(engine: Engine, now: datetime | None = None) -> bool:
    """True when no run exists, or the newest one started more than RUN_STALE_AFTER_HOURS ago."""
    latest = next(iter(list_runs(engine, 1)), None)
    if latest is None:
        return True
    started: datetime = latest["started_at"]
    if started.tzinfo is None:  # SQLite returns naive UTC
        started = started.replace(tzinfo=UTC)
    age = (now or datetime.now(UTC)) - started
    return age > timedelta(hours=params.RUN_STALE_AFTER_HOURS)


def start_catch_up_if_stale(engine: Engine) -> bool:
    """Start a background run when the evidence is stale; the lock skips it if one is running."""
    if not is_stale(engine):
        return False
    threading.Thread(target=run_pipeline, args=(engine, "catch-up"), daemon=True).start()
    return True


def main() -> None:
    from src.config import load_settings
    from src.db import init_db, make_engine
    from src.envfile import load_env_file

    parser = argparse.ArgumentParser(description="Run the Qart.ai evidence pipeline once.")
    parser.add_argument("--trigger", default="manual", choices=["manual", "schedule", "admin"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_env_file()
    engine = make_engine(load_settings().database_url)
    init_db(engine)
    summary = run_pipeline(engine, args.trigger)
    logger.info(
        "run %s: %s, %d new observations", summary.run_id, summary.status, summary.new_observations
    )
    for result in summary.sources:
        logger.info(
            "  %s: %s (%s new) %s %s",
            result["source_id"],
            result["status"],
            result.get("new", 0),
            result.get("note", ""),
            result.get("error", ""),
        )


if __name__ == "__main__":
    main()
