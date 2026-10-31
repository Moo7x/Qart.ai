"""Measured time from "Start" to ranked roles and a chosen plan (Phase 1 target: 80% < 5 min).

The intake records how long a person took from pressing Start to "Build my picture"
(`ProfileData.intake_seconds`); the profile row records when they then chose a destination, which
opens their plan. Their sum is the time to roles and a plan. Only new profiles that went through
the intake and chose a destination are counted, and nothing about the person is stored for it.
"""

import statistics
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, select

from src import params
from src.journey.store import profile_table


def _seconds(later: datetime, earlier: datetime) -> float:
    return max(0.0, (later - earlier).total_seconds())


def time_to_plan(engine: Engine) -> dict[str, Any]:
    with engine.connect() as conn:
        rows = conn.execute(
            select(
                profile_table.c.data,
                profile_table.c.created_at,
                profile_table.c.destination_chosen_at,
            ).where(profile_table.c.destination_chosen_at.is_not(None))
        ).all()
    times = sorted(
        float(data["intake_seconds"]) + _seconds(chosen, created)
        for data, created, chosen in rows
        if isinstance(data, dict) and data.get("intake_seconds") is not None
    )
    target = params.TIME_TO_PLAN_TARGET_SECONDS
    return {
        "people": len(times),
        "median_seconds": round(statistics.median(times)) if times else None,
        "under_target": sum(t <= target for t in times),
        "target_seconds": target,
        "target_share": params.TIME_TO_PLAN_TARGET_SHARE,
        "kind": "observed",
    }
