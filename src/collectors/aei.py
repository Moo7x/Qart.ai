"""Anthropic Economic Index: how much of Claude's sampled usage maps to each finance occupation.

We keep, for the field's occupations, the share of conversations (`pct`, global and Malaysia) and
the global split between automation-style and augmentation-style use. Months are compared only
within one release, because earlier releases used a different sampling method.

The newest release file is about 220 MB, so it is streamed and filtered row by row, and a release
already ingested is not downloaded again (remembered in the source state).
"""

import csv
import re
from collections.abc import Iterable, Iterator
from pathlib import Path

import httpx

from src.collectors.base import CollectorResult, SourceState
from src.config import REPO_ROOT
from src.evidence.field import field_profile
from src.evidence.store import Observation

SOURCE_ID = "anthropic_economic_index"
TREE_API = "https://huggingface.co/api/datasets/Anthropic/EconomicIndex/tree/main"
RESOLVE = "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/"
RELEASE_DIR = re.compile(r"^release_(\d{4})_(\d{2})_(\d{2})$")
CLAUDE_AI_FILE = re.compile(r"aei_claude_ai_(\d{4}-\d{2}-\d{2})\.csv$")
STATE_KEY = "release"
METHOD_VERSION = "aei/monthly-2026"  # the monthly schema introduced with release 2026-06-26
GLOBAL_METRICS = {
    "pct": "% of sampled conversations",
    "collaboration_bucket_automation_pct": "% of this occupation's conversations",
    "collaboration_bucket_augmentation_pct": "% of this occupation's conversations",
}
COUNTRY_METRICS = {"pct": "% of sampled conversations"}  # countries publish only `pct` here


def latest_release(client: httpx.Client) -> tuple[str, str, str] | None:
    """(release folder, release date, CSV path) of the newest release in the monthly format."""
    folders = client.get(TREE_API)
    folders.raise_for_status()
    releases = sorted(
        (
            e["path"]
            for e in folders.json()
            if e["type"] == "directory" and RELEASE_DIR.match(e["path"])
        ),
        reverse=True,
    )
    for release in releases:
        files = client.get(f"{TREE_API}/{release}/data")
        files.raise_for_status()
        for entry in files.json():
            match = CLAUDE_AI_FILE.search(entry["path"])
            if entry["type"] == "file" and match:
                return release, match.group(1), entry["path"]
    return None


def local_copy(release: str, csv_path: str) -> Path:
    """Where a developer may keep the same file (gitignored data/raw/aei_YYYY_MM_DD/)."""
    return REPO_ROOT / "data" / "raw" / release.replace("release_", "aei_") / Path(csv_path).name


def stream_lines(client: httpx.Client, url: str) -> Iterator[str]:
    with client.stream("GET", url, follow_redirects=True) as response:
        response.raise_for_status()
        yield from response.iter_lines()


def parse_rows(lines: Iterable[str], release_date: str, url: str) -> list[Observation]:
    codes = field_profile().soc_codes()
    observations = []
    for row in csv.DictReader(lines):
        if row["category_name"] != "soc_occupation" or row["node_external_id"] not in codes:
            continue
        metrics = GLOBAL_METRICS if row["geo_id"] == "GLOBAL" else COUNTRY_METRICS
        if (
            row["geo_id"] not in ("GLOBAL", field_profile().country)
            or row["metric_id"] not in metrics
        ):
            continue
        observations.append(
            Observation(
                source_id=SOURCE_ID,
                series=f"aei_{row['metric_id']}",
                entity=f"{row['node_external_id']} {row['node_name']}",
                geography=row["geo_id"],
                period=row["date_start"][:7],
                value=float(row["value"]) if row["value"] != "" else None,
                unit=metrics[row["metric_id"]],
                url=url,
                cited_span=(
                    f"{row['date_start']}..{row['date_end']} · {row['geo_id']} · "
                    f"soc_occupation · {row['metric_id']} = {row['value']} · "
                    f"{row['node_name']} ({row['node_external_id']})"
                ),
                method_version=METHOD_VERSION,
                published=release_date,
            )
        )
    return observations


def collect(client: httpx.Client, state: SourceState) -> CollectorResult:
    found = latest_release(client)
    if found is None:
        return CollectorResult([], note="no release in the monthly format was found")
    release, release_date, csv_path = found
    if state.get(STATE_KEY) == release:
        return CollectorResult([], note=f"no new release since {release_date}")
    url = RESOLVE + csv_path
    local = local_copy(release, csv_path)
    if local.exists():
        with local.open(encoding="utf-8", newline="") as handle:
            observations = parse_rows(handle, release_date, url)
    else:
        observations = parse_rows(stream_lines(client, url), release_date, url)
    state.set(STATE_KEY, release)
    return CollectorResult(observations, note=f"release {release_date}")
