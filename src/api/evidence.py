"""Evidence routes: registered sources, signals, observations, pipeline runs and the backtest."""

import hmac
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import Engine

from src import params
from src.config import Settings
from src.evidence import measures
from src.evidence.forecast import forecasts
from src.evidence.models import history
from src.evidence.registry import registry
from src.evidence.signals import Signal, build_signals
from src.evidence.store import (
    close_stale_runs,
    latest_observation_id,
    list_runs,
    query_observations,
)
from src.evidence.trends import trends
from src.match.evidence import automation_evidence
from src.pack import load_pack
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
    # Robustness (docs/PHASE2_PLAN.md A4): when the latest attempt failed, the screens keep using
    # the stored data, fetched at `serving_snapshot_from`, and say so.
    last_attempt_at: str | None  # start of the latest run that included this source
    last_success_at: str | None  # end of the latest run in which this source succeeded
    serving_snapshot_from: str | None  # newest stored observation's fetch time


SOURCE_HISTORY_RUNS = 50  # runs searched for a source's last success


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
    close_stale_runs(engine, timedelta(minutes=params.RUN_WATCHDOG_MINUTES))
    history = list_runs(engine, SOURCE_HISTORY_RUNS)
    out = []
    for source in registry().values():
        mine = [r for r in rows if r["source_id"] == source.id]
        fetched = max((r["fetched_at"] for r in mine), default=None)
        tried = [(run, s) for run in history for s in run["sources"] if s["source_id"] == source.id]
        attempt, result = tried[0] if tried else (None, {})
        success = next((run for run, s in tried if s["status"] == "ok"), None)
        out.append(
            SourceStatus(
                **source.model_dump(exclude={"collector", "docs_url"}),
                observations=len(mine),
                last_fetched=fetched.isoformat() if fetched else None,
                last_status=result.get("status"),
                last_note=result.get("note") or result.get("error"),
                last_attempt_at=attempt["started_at"].isoformat() if attempt else None,
                last_success_at=(
                    success["finished_at"].isoformat()
                    if success and success["finished_at"]
                    else None
                ),
                serving_snapshot_from=fetched.isoformat() if fetched else None,
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
    close_stale_runs(engine, timedelta(minutes=params.RUN_WATCHDOG_MINUTES))
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


@router.get("/trends")
def trend_series(engine: Engine = Depends(get_engine)) -> dict[str, Any]:
    """Rising and declining series for the Trends page, each labelled by kind in the UI."""
    rows = query_observations(engine)
    return trends(load_pack(), rows, automation_evidence(rows))


class HistoryPoint(BaseModel):
    period: str
    value: float


class ForecastPoint(BaseModel):
    period: str
    point: float
    low: float | None
    high: float | None


class SeriesForecast(BaseModel):
    """One forecast series or outlook (docs/PHASE2_PLAN.md C8); every value is an estimate."""

    series_id: str
    kind: Literal["employment_share", "job_ads", "role_outlook", "skill_outlook"]
    title: str
    history: list[HistoryPoint]
    forecast: list[ForecastPoint]
    model: str | None
    baseline: str
    backtest: dict[str, Any] | None
    label: Literal["estimate"]
    source: str
    fetched_at: str | None
    note: str
    components: dict[str, Any] | None = None


_forecast_cache: dict[int, list[SeriesForecast]] = {}


@router.get("/forecast")
def forecast_series(engine: Engine = Depends(get_engine)) -> list[SeriesForecast]:
    """Forecasts with their backtest and the role and skill outlooks, recomputed on new data."""
    latest = latest_observation_id(engine)
    if latest not in _forecast_cache:
        rows = query_observations(engine)
        _forecast_cache.clear()  # only the newest data's forecasts are kept
        _forecast_cache[latest] = [
            SeriesForecast.model_validate(entry)
            for entry in forecasts(load_pack(), rows, automation_evidence(rows))
        ]
    return _forecast_cache[latest]


@router.get("/pipeline/forecast-check")
def forecast_check(engine: Engine = Depends(get_engine)) -> list[dict[str, Any]]:
    """Rolling-origin errors per occupation group and horizon, from all stored years."""
    shares = measures.occupation_shares(
        query_observations(engine, source_id="dosm_wages_occupation")
    )
    return [
        {"group": group, **measures.rolling_backtest(series, horizon)}
        for group, series in sorted(shares.items())
        for horizon in params.ROLLING_HORIZONS
    ]


@router.get("/pipeline/models")
def model_versions(engine: Engine = Depends(get_engine)) -> list[dict[str, Any]]:
    """Every stored trend-model version with its backtest errors, oldest first per group."""
    return history(engine)


@router.post("/pipeline/run", status_code=202)
def run_now(
    background: BackgroundTasks,
    engine: Engine = Depends(get_engine),
    settings: Settings = Depends(get_settings),
    x_admin_token: str | None = Header(default=None),
    trigger: Literal["admin", "schedule"] = Query(default="admin"),
) -> RunStarted:
    """Admin only. Starts a run in the background; GET /pipeline/runs shows its result.

    `trigger=schedule` is what the daily GitHub Actions workflow sends, so its runs are logged as
    scheduled rather than as an admin pressing Run now.
    """
    if not settings.admin_token:
        raise HTTPException(
            status_code=503, detail="Run now is disabled: QART_ADMIN_TOKEN is not set"
        )
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=403, detail="admin token required")
    background.add_task(run_pipeline, engine, trigger)
    return RunStarted(
        status="started",
        note=f"a run started; if one is already running ({LOCK_NAME} lock) it is skipped",
    )
