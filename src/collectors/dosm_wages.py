"""OpenDOSM `wages_occupation`: employees and their pay by major occupation group, per year.

We store each group's headcount and the overall total (series `employees`), and the published
median and mean monthly wage (series `wages_median`, `wages_mean`); shares are computed later by
the measures module, so the stored facts stay exactly what DOSM published. Pay is the pay of all
employees in a major group, shown beside roles in that group; it never enters a score.
The pay series keep the same method version: they come from the same rows, read the same way, so
the existing headcount observations are not stored again.
"""

from typing import Any

import httpx

from src.collectors.base import CollectorResult, SourceState
from src.evidence.registry import registry
from src.evidence.store import Observation

SOURCE_ID = "dosm_wages_occupation"
API_URL = "https://api.data.gov.my/data-catalogue/"
DATASET_ID = "wages_occupation"
ROW_LIMIT = 5000  # the whole dataset is about 500 rows; the limit only guards the request
METHOD_VERSION = "dosm_wages/1"
UNIT = "thousand persons"
PAY_UNIT = "RM per month"
PAY_SERIES = {"wages_median": "wages_median", "wages_mean": "wages_mean"}  # series -> row field


def fetch(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.get(API_URL, params={"id": DATASET_ID, "limit": ROW_LIMIT})
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise ValueError("unexpected wages_occupation response: not a list of rows")
    return rows


def _observation(row: dict[str, Any], series: str, field: str, unit: str, url: str) -> Observation:
    value = row.get(field)
    return Observation(
        source_id=SOURCE_ID,
        series=series,
        entity=str(row["occupation"]),
        geography="MYS",
        period=str(row["date"])[:4],
        value=float(value) if value is not None else None,  # missing stays missing, never zero
        unit=unit,
        url=url,
        cited_span=(
            f"wages_occupation · {row['date']} · occupation={row['occupation']} · "
            f"sex=both · {field}={value}"
        ),
        method_version=METHOD_VERSION,
        published=None,
    )


def parse(rows: list[dict[str, Any]]) -> list[Observation]:
    """Both-sexes headcount and pay per occupation group and year, the row as the cited span."""
    url = registry()[SOURCE_ID].url
    observations = []
    for row in rows:
        if row.get("sex") != "both":
            continue
        observations.append(_observation(row, "employees", "recipients", UNIT, url))
        observations += [
            _observation(row, series, field, PAY_UNIT, url) for series, field in PAY_SERIES.items()
        ]
    return observations


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    observations = parse(fetch(client))
    years = sorted({o.period for o in observations if o.series == "employees"})
    return CollectorResult(observations, note=f"years {years[0]}–{years[-1]}" if years else "")
