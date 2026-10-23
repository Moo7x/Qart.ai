"""OpenDOSM `wages_occupation`: wage recipients (employees) by major occupation group, per year.

We store each group's headcount and the overall total; shares are computed later by the measures
module, so the stored facts stay exactly what DOSM published.
"""

from typing import Any

import httpx

from src.evidence.registry import registry
from src.evidence.store import Observation

SOURCE_ID = "dosm_wages_occupation"
API_URL = "https://api.data.gov.my/data-catalogue/"
DATASET_ID = "wages_occupation"
ROW_LIMIT = 5000  # the whole dataset is about 500 rows; the limit only guards the request
METHOD_VERSION = "dosm_wages/1"
UNIT = "thousand persons"


def fetch(client: httpx.Client) -> list[dict[str, Any]]:
    response = client.get(API_URL, params={"id": DATASET_ID, "limit": ROW_LIMIT})
    response.raise_for_status()
    rows = response.json()
    if not isinstance(rows, list):
        raise ValueError("unexpected wages_occupation response: not a list of rows")
    return rows


def parse(rows: list[dict[str, Any]]) -> list[Observation]:
    """Both-sexes headcount per occupation group and year, with the row as the cited span."""
    url = registry()[SOURCE_ID].url
    observations = []
    for row in rows:
        if row.get("sex") != "both":
            continue
        year = str(row["date"])[:4]
        recipients = row.get("recipients")
        observations.append(
            Observation(
                source_id=SOURCE_ID,
                series="employees",
                entity=str(row["occupation"]),
                geography="MYS",
                period=year,
                value=float(recipients) if recipients is not None else None,
                unit=UNIT,
                url=url,
                cited_span=(
                    f"wages_occupation · {row['date']} · occupation={row['occupation']} · "
                    f"sex=both · recipients={recipients}"
                ),
                method_version=METHOD_VERSION,
                published=None,
            )
        )
    return observations


def collect(client: httpx.Client) -> list[Observation]:
    return parse(fetch(client))
