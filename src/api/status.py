"""Status: data freshness, runs, fallbacks, usage and cost, fairness result, platform SDG totals.

docs/PHASE2_PLAN.md A9 and contract C9. Owner: A (p2-ai-experience). Registered in src/app.py
in Stage 0; routes are added here only.

Everything here is measured from the app's own tables (runs, observations, the usage counter),
except the cost, which multiplies measured usage by declared prices and is labelled an estimate.
The fairness check and the platform SDG totals come from owner B's code; until it is merged they
are reported as not available, never as zero.
"""

from datetime import timedelta
from importlib import import_module
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from src import params, usage
from src.api.evidence import get_engine, get_settings, sources
from src.config import Settings
from src.evidence.store import close_stale_runs, list_runs

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


def _from_owner_b(module: str, name: str) -> Any:
    """A function from owner B's code if it is merged, else None (shown as not available)."""
    try:
        return getattr(import_module(module), name)
    except (ImportError, AttributeError):
        return None


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
    fairness = _from_owner_b("src.match.fairness", "paired_profile_check")
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
            "total_usd": round(sum(r["cost_usd"] or 0 for r in totals), 4),
            "prices_checked": params.PRICES_CHECKED,
            "gpu_price_set": params.RUNPOD_USD_PER_SECOND is not None,
            "note": "Measured calls and tokens × declared list prices; GPU cost needs the "
            "endpoint's per-second price.",
        },
        "fairness": {"available": fairness is not None},
        "platform_sdg": {"available": _from_owner_b("src.pathway.sdg", "sdg_matrix") is not None},
    }
