"""Qart's own forecast: the industry roles and skills by category, with the task model behind it.

GET /api/forecast/industry?scenario=moderate|fast — every number is an estimate (forecast) or an
observation with its source; the task model's cross-validated error is returned with it.
"""

import json
from typing import Any, Literal

from fastapi import APIRouter, Depends
from sqlalchemy import Engine

from src.api.evidence import get_engine
from src.evidence.store import query_observations
from src.forecast import task_model
from src.forecast.industry import industry
from src.pack import load_pack

router = APIRouter(prefix="/api/forecast")


def model_summary(version: dict[str, Any] | None) -> dict[str, Any] | None:
    """What the task model is and how well it did, for the method note beside the forecast."""
    if version is None:
        return None
    scores = json.loads(version["scores"])
    best = version["best"]
    return {
        "version": version["id"],
        "trained": version["created_at"].isoformat() if version["created_at"] else None,
        "period": version["period"],
        "features": version["features"],
        "training_tasks": version["n_train"],
        "predicted_tasks": version["n_predict"],
        "best": best,
        "mae": scores.get(best),
        "baseline_mae": scores.get("mean"),
        "scores": scores,
        "source": "Anthropic Economic Index (task-level automation share) and O*NET 31.0 tasks",
    }


@router.get("/industry")
def industry_forecast(
    scenario: Literal["moderate", "fast"] = "moderate", engine: Engine = Depends(get_engine)
) -> dict[str, Any]:
    version, tasks = task_model.latest(engine)
    out = industry(load_pack(), query_observations(engine), tasks, scenario)
    return {**out, "task_model": model_summary(version), "kind": "estimate"}
