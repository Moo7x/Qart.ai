"""Status: data freshness, runs, fallbacks, usage and cost, fairness result, platform SDG totals.

docs/PHASE2_PLAN.md A9 and contract C9. Owner: A (p2-ai-experience). Registered in src/app.py
in Stage 0; routes are added here only.

Everything here is measured from the app's own tables (runs, observations, the usage counter),
except the cost, which multiplies measured usage by declared prices and is labelled an estimate.
The fairness check (C10) and the SDG planner (C4) are owner B's code; this page only runs and
shows them. Platform SDG totals add up planned hours over every person with a destination, and are
withheld while fewer than PLATFORM_SDG_MIN_PROFILES people have one (AGENTS.md: groups under 5).
"""

from collections import defaultdict
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import Engine, func, select

from src import params, usage
from src.api.evidence import get_engine, get_settings, sources
from src.config import Settings
from src.evidence.store import (
    close_stale_runs,
    latest_observation_id,
    list_runs,
    query_observations,
)
from src.journey.impact import time_to_plan
from src.journey.person import load_person
from src.journey.store import profile_table
from src.match.evidence import automation_evidence
from src.match.fairness import paired_profile_check
from src.pack import load_pack
from src.pathway.sdg import sdg_matrix

router = APIRouter(prefix="/api")

RUNS_SHOWN = 12
TOKENS_PER_MILLION = 1_000_000


def cost_rows(totals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Measured usage with its estimated cost (USD) where a price is declared."""
    out = []
    for row in totals:
        price = params.PRICES_PER_MILLION_TOKENS.get(row["model"])
        cost: float | None = None
        if row["engine"] == "openai" and price:
            cost = (
                row["tokens_in"] * price["in"] + row["tokens_out"] * price["out"]
            ) / TOKENS_PER_MILLION
        elif row["engine"] == "runpod" and params.RUNPOD_USD_PER_SECOND is not None:
            cost = row["seconds"] * params.RUNPOD_USD_PER_SECOND
        out.append({**row, "cost_usd": round(cost, 4) if cost is not None else None})
    return out


# Both results are recomputed only when their inputs change: the evidence high-water id for the
# fairness check, and that id plus the profiles' last update for the platform totals.
_fairness_cache: dict[int, dict[str, Any]] = {}
_platform_cache: dict[tuple[int, int, str], list[dict[str, Any]]] = {}


def fairness(engine: Engine) -> dict[str, Any]:
    """The paired-profile check (C10) on the current evidence, with the date it ran."""
    upto = latest_observation_id(engine)
    if upto not in _fairness_cache:
        _fairness_cache.clear()
        evidence = automation_evidence(query_observations(engine, through_id=upto))
        _fairness_cache[upto] = paired_profile_check(load_pack(), evidence)
    return {"available": True, **_fairness_cache[upto]}


def platform_sdg(engine: Engine) -> dict[str, Any]:
    """Planned study hours per SDG target, added up over everyone with a destination.

    Each person's plan is the one they see (their scenario default, their evidence cutoff). Hours
    of one skill count toward every target it serves, so the totals are not additive across
    targets.
    """
    with engine.connect() as conn:
        count, last = conn.execute(
            select(func.count(), func.max(profile_table.c.updated_at)).where(
                profile_table.c.destination.is_not(None)
            )
        ).one()
    base = {
        "available": True,
        "profiles": int(count),
        "min_profiles": params.PLATFORM_SDG_MIN_PROFILES,
    }
    if count < params.PLATFORM_SDG_MIN_PROFILES:
        return {**base, "suppressed": True, "totals": []}
    key = (latest_observation_id(engine), int(count), str(last))
    if key not in _platform_cache:
        _platform_cache.clear()
        _platform_cache[key] = _platform_totals(engine)
    return {**base, "suppressed": False, "totals": _platform_cache[key]}


def _platform_totals(engine: Engine) -> list[dict[str, Any]]:
    pack = load_pack()
    hours: dict[str, float] = defaultdict(float)
    with engine.connect() as conn:
        rows = conn.execute(
            select(profile_table.c.id, profile_table.c.data, profile_table.c.destination).where(
                profile_table.c.destination.is_not(None)
            )
        ).all()
    for profile_id, _, destination in rows:
        person = load_person(engine, profile_id)
        if person is None or destination not in pack.destination_roles:
            continue  # deleted meanwhile, or a role removed from the pack since it was chosen
        plan = person.plan(person.score(destination, "moderate"), "moderate")
        for total in sdg_matrix(pack, plan).totals:
            hours[total.target] += total.hours
    return [{"target": t, "hours": round(h, 1)} for t, h in sorted(hours.items())]


@router.get("/status")
def status(
    engine: Engine = Depends(get_engine), settings: Settings = Depends(get_settings)
) -> dict[str, Any]:
    close_stale_runs(engine, timedelta(minutes=params.RUN_WATCHDOG_MINUTES))
    totals = cost_rows(usage.totals(engine))
    by_engine: dict[str, dict[str, int]] = {}
    for row in totals:
        e = by_engine.setdefault(row["engine"], {"calls": 0, "failed": 0})
        e["calls"] += int(row["calls"])
        e["failed"] += int(row["failed"])
    total_usd = round(sum(r["cost_usd"] or 0 for r in totals), 4)
    with engine.connect() as conn:
        people = int(conn.execute(select(func.count()).select_from(profile_table)).scalar_one())
    per_person = total_usd / people if people else None
    return {
        "sources": [s.model_dump() for s in sources(engine)],
        "runs": list_runs(engine, RUNS_SHOWN),
        "schedule": "Daily, by the separate scheduled deployment (qart-pipeline); opening the app "
        f"also starts a run when the newest one is older than {params.RUN_STALE_AFTER_HOURS} h.",
        "engines": {
            "language_model": {
                "configured": settings.llm_configured,
                "models": [settings.llm_model, settings.agent_model],
                **by_engine.get("openai", {"calls": 0, "failed": 0}),
            },
            "gpu": {
                "configured": settings.runpod_configured,
                "models": ["BAAI/bge-m3", "BAAI/bge-reranker-v2-m3"],
                **by_engine.get("runpod", {"calls": 0, "failed": 0}),
            },
        },
        "usage": totals,
        "cost": {
            "label": "estimate",
            "total_usd": total_usd,
            # Measured cost per profile, and what that means per month at a given number of new
            # people (estimate: assumes future people use the app as the measured ones did).
            "profiles": people,
            "per_person_usd": round(per_person, 5) if per_person is not None else None,
            "per_month_usd": {
                str(n): round(per_person * n, 2) for n in params.COST_PEOPLE_PER_MONTH
            }
            if per_person is not None
            else {},
            "prices_checked": params.PRICES_CHECKED,
            "gpu_price_set": params.RUNPOD_USD_PER_SECOND is not None,
            "note": "Measured calls and tokens Ã— declared list prices; GPU cost needs the "
            "endpoint's per-second price.",
        },
        "fairness": fairness(engine),
        "platform_sdg": platform_sdg(engine),
        "time_to_plan": time_to_plan(engine),
    }
