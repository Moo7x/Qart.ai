"""Evidence routes: registered sources, signals, observations, pipeline runs and the backtest."""

import hmac
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import Engine

from src.config import Settings
from src.evidence import measures
from src.evidence.registry import registry
from src.evidence.signals import Signal, build_signals
from src.evidence.store import list_runs, query_observations
from src.pipeline.run import LOCK_NAME, run_pipeline, start_catch_up_if_stale

router = APIRouter(prefix="/api")

MAX_RUNS = 50
MAX_OBSERVATIONS = 2000


def get_engine(request: Request) -> Engine:
    engine: Engine = request.app.state.engine
    return engine


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


class SourceStatus(BaseModel):
    id: str
    name: str
    publisher: str
    family: str
    url: str
    terms: str
    terms_url: str
    terms_checked: str | None
    attribution: str
    tier: str
    cadence: str
    shows: str
    does_not_show: str
    notes: str
    observations: int
    last_fetched: str | None
    last_status: str | None  # ok / failed in the latest run that included this source
    last_note: str | None


class SignalsResponse(BaseModel):
    generated_at: str
    observations: int
    signals: list[Signal]


class BacktestEntry(BaseModel):
    group: str
    naive: float
    linear: float
    damped: float
    best: str


class RunStarted(BaseModel):
    status: Literal["started"]
    note: str


@router.get("/sources")
def sources(engine: Engine = Depends(get_engine)) -> list[SourceStatus]:
    rows = query_observations(engine)
    latest_run = next(iter(list_runs(engine, 1)), None)
    by_source = {r["source_id"]: r for r in (latest_run or {}).get("sources", [])}
    out = []
    for source in registry().values():
        mine = [r for r in rows if r["source_id"] == source.id]
        fetched = max((r["fetched_at"] for r in mine), default=None)
        result = by_source.get(source.id, {})
        out.append(
            SourceStatus(
                **source.model_dump(exclude={"collector", "docs_url"}),
                observations=len(mine),
                last_fetched=fetched.isoformat() if fetched else None,
                last_status=result.get("status"),
                last_note=result.get("note") or result.get("error"),
            )
        )
    return out


@router.get("/signals")
def signals(request: Request, engine: Engine = Depends(get_engine)) -> SignalsResponse:
    # Opening the overview checks freshness: a backup for the scheduled job (see params).
    if request.app.state.catch_up:
        start_catch_up_if_stale(engine)
    rows = query_observations(engine)
    return SignalsResponse(
        generated_at=datetime.now(UTC).isoformat(),
        observations=len(rows),
        signals=build_signals(rows),
    )


@router.get("/observations")
def observations(
    engine: Engine = Depends(get_engine),
    source_id: str | None = Query(default=None, max_length=64),
    series: str | None = Query(default=None, max_length=128),
) -> list[dict[str, Any]]:
    if source_id is not None and source_id not in registry():
        raise HTTPException(status_code=404, detail=f"unknown source {source_id}")
    rows = query_observations(engine, source_id=source_id, series=series)[:MAX_OBSERVATIONS]
    return [{k: v for k, v in r.items() if k != "content_hash"} for r in rows]


@router.get("/pipeline/runs")
def runs(
    engine: Engine = Depends(get_engine), limit: int = Query(default=20, ge=1, le=MAX_RUNS)
) -> list[dict[str, Any]]:
    return list_runs(engine, limit)


@router.get("/pipeline/backtest")
def backtest(engine: Engine = Depends(get_engine)) -> list[BacktestEntry]:
    shares = measures.occupation_shares(
        query_observations(engine, source_id="dosm_wages_occupation")
    )
    entries = []
    for group, series in sorted(shares.items()):
        row = measures.backtest(series, group)
        entries.append(
            BacktestEntry(
                group=group,
                naive=round(row.naive, 3),
                linear=round(row.linear, 3),
                damped=round(row.damped, 3),
                best=row.best,
            )
        )
    return entries


@router.post("/pipeline/run", status_code=202)
def run_now(
    background: BackgroundTasks,
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
    x_admin_token: str | None = Header(default=None),
) -> RunStarted:
    """Admin only. Starts a run in the background; GET /pipeline/runs shows its result."""
    if not settings.admin_token:
        raise HTTPException(
            status_code=503, detail="Run now is disabled: QART_ADMIN_TOKEN is not set"
        )
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=403, detail="admin token required")
    background.add_task(run_pipeline, engine, "admin")
    return RunStarted(
        status="started",
        note=f"a run started; if one is already running ({LOCK_NAME} lock) it is skipped",
    )
