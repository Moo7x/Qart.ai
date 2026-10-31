"""Pay on a role card (docs/PHASE2_PLAN.md §4 C11): the occupation group's monthly wage, observed.

The OpenDOSM wages_occupation series (collected by A as `wages_median` and `wages_mean`, RM per
month) gives pay for all employees in a MASCO major group, not an offer for a role. The role's
group comes from its ISCO code (src/match/outlook.py MAJOR_GROUP). Pay is shown beside fit and
never changes fit, band or rank. Missing group, year or median gives None ("not published").
"""

from datetime import datetime
from typing import Any

from src.evidence.field import field_profile
from src.evidence.signals import FIELD_GROUPS
from src.match.outlook import MAJOR_GROUP
from src.pack import DestinationRole

SOURCE_ID = "dosm_wages_occupation"
SOURCE = "OpenDOSM wages_occupation"
UNIT = "RM per month"
NOTE = "Pay of all employees in this occupation group, not an offer for this role."
NATIONAL = "overall"


def _series(rows: list[dict[str, Any]], series: str, entity: str) -> dict[str, dict[str, Any]]:
    return {
        r["period"]: r
        for r in rows
        if r["source_id"] == SOURCE_ID
        and r["series"] == series
        and r["entity"] == entity
        and r["value"] is not None
    }


def role_pay(role: DestinationRole, rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    occupation = field_profile().occupation(role.soc)
    group = MAJOR_GROUP.get(occupation.isco[0]) if occupation and occupation.isco else None
    if group is None:
        return None
    median = _series(rows, "wages_median", group)
    if not median:
        return None
    year = max(median)
    row = median[year]
    mean = _series(rows, "wages_mean", group).get(year)
    overall = _series(rows, "wages_median", NATIONAL).get(year)
    fetched = row.get("fetched_at")
    return {
        "group": group,
        "group_title": FIELD_GROUPS.get(group, group),
        "year": year,
        "median": row["value"],
        "mean": mean["value"] if mean else None,
        "overall_median": overall["value"] if overall else None,
        "unit": UNIT,
        "kind": "observed",
        "source": SOURCE,
        "fetched_at": fetched.isoformat() if isinstance(fetched, datetime) else str(fetched or ""),
        "cited_span": row.get("cited_span", ""),
        "note": NOTE,
    }
