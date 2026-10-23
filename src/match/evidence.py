"""Observed inputs to matching, read from the evidence store (never typed in by hand)."""

from typing import Any

from src.evidence import measures
from src.match.engine import Evidence

AUTOMATION_METRIC = "collaboration_bucket_automation_pct"
SOURCE = "Anthropic Economic Index (global, share of automation-style conversations)"


def automation_evidence(rows: list[dict[str, Any]]) -> Evidence:
    """Latest month's automation-style share per SOC code."""
    series = measures.aei_series(rows, AUTOMATION_METRIC, "GLOBAL")
    shares: dict[str, float] = {}
    period = ""
    for entity, points in series.items():
        if points:
            shares[entity.split(" ", 1)[0]] = points[-1][1]
            period = max(period, points[-1][0])
    return Evidence(automation_share=shares, automation_period=period, automation_source=SOURCE)
