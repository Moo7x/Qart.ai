"""Trend model versions (PLAN §4.3 step 7): the backtest re-scored whenever its data changes.

After every pipeline run the DOSM occupation-share backtest is recomputed from all comparable
years stored so far. A new version is stored only when a group's data changed (a new year, or a
revised value): it records the years used, the test years and each model's error, so the Live
intelligence page can show forecast error over time. A run that brings no new data for a group
stores nothing and says the model is unchanged. Nothing here claims an improvement: a version
only reports the errors it measured.
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    Column,
    DateTime,
    Engine,
    Float,
    Integer,
    String,
    Table,
    insert,
    select,
)

from src import params
from src.db import metadata
from src.evidence import measures
from src.evidence.store import query_observations

model_table = Table(
    "model_version",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("group_id", String(64), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("run_id", Integer, nullable=True),
    Column("first_year", String(8), nullable=False),
    Column("last_year", String(8), nullable=False),
    Column("points", Integer, nullable=False),
    Column("train_end", Integer, nullable=False),
    Column("test_years", String(16), nullable=False),
    Column("naive", Float, nullable=False),
    Column("linear", Float, nullable=False),
    Column("damped", Float, nullable=False),
    Column("best", String(16), nullable=False),
    Column("data_hash", String(64), nullable=False),
)


def _digest(series: list[measures.Point]) -> str:
    return hashlib.sha256(json.dumps(series).encode()).hexdigest()


def latest_versions(engine: Engine) -> dict[str, dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(select(model_table).order_by(model_table.c.id)).mappings()
        return {r["group_id"]: dict(r) for r in rows}


def record_versions(engine: Engine, run_id: int | None) -> dict[str, Any]:
    """Store a version for every group whose data changed; a run-log entry describes the result."""
    shares = measures.occupation_shares(
        query_observations(engine, source_id="dosm_wages_occupation")
    )
    previous = latest_versions(engine)
    changed: list[str] = []
    first: list[str] = []
    with engine.begin() as conn:
        for group, series in sorted(shares.items()):
            digest = _digest(series)
            if group in previous and previous[group]["data_hash"] == digest:
                continue
            try:
                row = measures.backtest(series, group)
            except ValueError:
                continue  # too few years to score: nothing to version yet
            test = [p for p, _ in series if int(p) > params.BACKTEST_TRAIN_END]
            conn.execute(
                insert(model_table).values(
                    group_id=group,
                    created_at=datetime.now(UTC),
                    run_id=run_id,
                    first_year=series[0][0],
                    last_year=series[-1][0],
                    points=len(series),
                    train_end=params.BACKTEST_TRAIN_END,
                    test_years=f"{test[0]}–{test[-1]}",
                    naive=row.naive,
                    linear=row.linear,
                    damped=row.damped,
                    best=row.best,
                    data_hash=digest,
                )
            )
            (changed if group in previous else first).append(f"{group} ({series[-1][0]})")
    parts = []
    if first:
        parts.append(f"first backtest version stored: {', '.join(first)}")
    if changed:
        parts.append(f"backtest re-scored with new data: {', '.join(changed)}")
    note = "; ".join(parts) or "no new DOSM data: trend models unchanged"
    return {"source_id": "trend_models", "status": "ok", "fetched": 0, "new": 0, "note": note}


def history(engine: Engine) -> list[dict[str, Any]]:
    """Every stored version, oldest first per group."""
    with engine.connect() as conn:
        rows = conn.execute(
            select(model_table).order_by(model_table.c.group_id, model_table.c.id)
        ).mappings()
        return [dict(r) for r in rows]
