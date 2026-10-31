"""Directions: today's person matched to tomorrow's roles, using fit and the industry forecast.

For every destination role this adds what the industry forecast says about it (src/forecast/
industry.py: growing, transforming, shrinking, emerging or stable, with the reasons), how close the
move is, and the order the roles are shown in:

    direction score = fit x OUTLOOK_FACTOR[category]      (declared factors, src/params.py)

so a role with a better outlook moves above a role with a similar fit, while the fit shown is the
person's own coverage, unchanged. A move is "adjacent" when O*NET's analysts relate the person's
current occupation to the role's (Related Occupations, top 10) or the occupation is the same, or
when the person already covers much of the role; otherwise it is a "stretch". The person's current
role gets its own forecast: where their job is heading (the basis of their reskilling path).
"""

from collections.abc import Sequence
from typing import Any

from src import params
from src.collectors.onet import RELATED_SERIES
from src.forecast.industry import industry
from src.match.engine import RoleMatch
from src.pack import Pack

Row = dict[str, Any]


def related_tier(rows: list[Row], from_soc: str | None, to_soc: str) -> int | None:
    """0 for the same occupation, O*NET's relatedness tier (1-3) if listed, else None."""
    if from_soc is None:
        return None
    if from_soc == to_soc:
        return 0
    tiers = [
        int(r["value"])
        for r in rows
        if r["series"] == RELATED_SERIES and r["entity"] == f"{from_soc} {to_soc}"
    ]
    return min(tiers) if tiers else None


def direction(fit: float, tier: int | None) -> str:
    close = tier is not None and tier <= params.DIRECTION_ADJACENT_TIER
    return "adjacent" if close or fit >= params.DIRECTION_ADJACENT_FIT else "stretch"


def forecasts(pack: Pack, rows: list[Row], task_rows: list[Row], scenario: str) -> dict[str, Row]:
    """The industry forecast keyed by pack role id (current and destination roles)."""
    view = industry(pack, rows, task_rows, scenario)
    return {r["pack_role"]: r for r in view["roles"] if r["pack_role"]}


def summary(forecast: Row | None) -> dict[str, Any] | None:
    """The part of a role's forecast a role card shows."""
    if forecast is None:
        return None
    return {
        "category": forecast["category"],
        "label": forecast["label"],
        "meaning": forecast["meaning"],
        "reasons": forecast["reasons"],
        "change_pp": forecast["demand"].get("change_pp"),
        "critical": forecast["demand"].get("critical"),
        "ai_use": forecast["ai"]["use"],
        "kind": "estimate",
    }


def factor(forecast: Row | None) -> float:
    return params.OUTLOOK_FACTOR.get(forecast["category"], 1.0) if forecast else 1.0


def order(matches: Sequence[RoleMatch], by_role: dict[str, Row]) -> list[RoleMatch]:
    """Roles by direction score, best first; equal scores keep the incoming order (near-ties)."""
    return sorted(matches, key=lambda m: -round(m.fit * factor(by_role.get(m.role_id)), 6))
