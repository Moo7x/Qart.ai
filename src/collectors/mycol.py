"""MyCOL 2024/2025: occupations Malaysia's Critical Skills Monitoring Committee lists as critical.

A versioned extraction (data/packs/gbs_fa/mycol_2024_2025.yaml): occupation names read by hand
with their page. The list is complete (66 names), so an occupation of the field that is not on it
is reported as "not listed", which is a fact about this edition, not a missing value. No network.
"""

from typing import Any

import httpx
import yaml

from src.collectors.base import CollectorResult, SourceState
from src.evidence.field import PACK_DIR
from src.evidence.store import Observation

SOURCE_ID = "mycol_2024_2025"
EXTRACTION = PACK_DIR / "mycol_2024_2025.yaml"
CRITICAL_SERIES = "mycol_critical_occupation"
PERSISTENT_SERIES = "mycol_persistent_occupation"
UNIT = "listed (1)"


def load_extraction() -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(EXTRACTION.read_text(encoding="utf-8"))
    return data


def parse(data: dict[str, Any]) -> list[Observation]:
    def listed(series: str, name: str, page: int) -> Observation:
        return Observation(
            source_id=SOURCE_ID,
            series=series,
            entity=name,
            geography="MYS",
            period=str(data["edition"]),
            value=1.0,
            unit=UNIT,
            url=str(data["url"]),
            cited_span=f"MyCOL {data['edition']} · PDF p. {page} · {name} · {data['document']}",
            method_version=str(data["version"]),
        )

    critical = data["critical_occupations"]
    persistent = data["persistent"]
    return [listed(CRITICAL_SERIES, name, critical["pdf_page"]) for name in critical["names"]] + [
        listed(PERSISTENT_SERIES, name, persistent["pdf_page"]) for name in persistent["names"]
    ]


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    data = load_extraction()
    return CollectorResult(parse(data), note=f"versioned extraction {data['version']}")
