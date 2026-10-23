"""Observed inputs to matching, read from the evidence store (never typed in by hand)."""

from typing import Any

from src.evidence import measures
from src.match.engine import Evidence

AUTOMATION_METRIC = "collaboration_bucket_automation_pct"
SOURCE = "Anthropic Economic Index (global, share of automation-style conversations)"
IMPORTANCE_SERIES = "onet_task_importance"
IMPORTANCE_SOURCE = "O*NET Database, task importance (USDOL/ETA, CC BY 4.0)"


def _latest(series: dict[str, list[measures.Point]]) -> tuple[dict[str, float], str]:
    """Latest point per entity, keyed by the entity's leading id (SOC code or task id)."""
    values: dict[str, float] = {}
    period = ""
    for entity, points in series.items():
        if points:
            values[entity.split(" ", 1)[0]] = points[-1][1]
            period = max(period, points[-1][0])
    return values, period


def automation_evidence(rows: list[dict[str, Any]]) -> Evidence:
    """Latest month's automation-style share per SOC code and per linked O*NET task."""
    shares, period = _latest(measures.aei_series(rows, AUTOMATION_METRIC, "GLOBAL"))
    tasks, task_period = _latest(measures.aei_series(rows, f"task_{AUTOMATION_METRIC}", "GLOBAL"))
    importance: dict[str, tuple[str, float]] = {}
    for row in rows:
        if row["series"] == IMPORTANCE_SERIES and row["value"] is not None:
            task = row["entity"].split(" ", 1)[0]
            if task not in importance or row["period"] >= importance[task][0]:
                importance[task] = (row["period"], float(row["value"]))
    return Evidence(
        automation_share=shares,
        automation_period=period,
        automation_source=SOURCE,
        task_automation=tasks,
        task_period=task_period,
        task_importance={task: value for task, (_, value) in importance.items()},
        task_importance_source=IMPORTANCE_SOURCE,
    )
