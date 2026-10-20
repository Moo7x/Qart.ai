"""Ingest the Anthropic Economic Index release into dated snapshots (Task A1, reusable/schedulable).

Usage:
    python -m src.engine.ingest            # build snapshots from data/raw (download if missing)
    python -m src.engine.ingest --offline  # never download; fail if the raw CSV is missing

Steps: download the claude_ai CSV into data/raw/ (gitignored, ~220 MB) → filter GLOBAL + MYS
finance SOC occupations and country-level collaboration shares → one Snapshot per monthly period
→ data/snapshots/snap_aei_YYYY_MM.json, each later period carrying its suggested reviews.
Data licence: CC-BY (Anthropic Economic Index); attribution is written into every snapshot.
"""

import argparse
import json
import logging
import urllib.request
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import pandas as pd

from src.contract import ReviewTrigger, Snapshot
from src.engine.catalogue import REPO_ROOT, default_catalogue
from src.engine.snapshots import AeiRow, build_snapshot

logger = logging.getLogger(__name__)

RELEASE = "release_2026_06_26"
RELEASE_DATE = "2026-06-26"
CSV_NAME = "aei_claude_ai_2026-06-26.csv"
CSV_URL = (
    "https://huggingface.co/datasets/Anthropic/EconomicIndex/resolve/main/"
    f"{RELEASE}/data/{CSV_NAME}"
)
RAW_DIR = REPO_ROOT / "data" / "raw" / "aei_2026_06_26"
SNAPSHOT_DIR = REPO_ROOT / "data" / "snapshots"

GEOS = ("GLOBAL", "MYS")
# Finance-related SOC occupations named in PERSON_A Task A1 (kept only if present in the data).
FINANCE_SOC_CODES = (
    "43-3031",  # Bookkeeping, Accounting, and Auditing Clerks
    "13-2011",  # Accountants and Auditors
    "13-2051",  # Financial and Investment Analysts
    "13-2031",  # Budget Analysts
    "43-3051",  # Payroll and Timekeeping Clerks
    "43-3021",  # Billing and Posting Clerks
    "13-1041",  # Compliance Officers
    "15-2051",  # Data Scientists
    "43-9111",  # Statistical Assistants
)
SOC_METRICS = (
    "pct",
    "collaboration_bucket_automation_pct",
    "collaboration_bucket_augmentation_pct",
)
OVERALL_METRICS = ("collaboration_bucket_automation_pct", "collaboration_bucket_augmentation_pct")
DETAILED_OCCUPATION_LEVEL = "0"  # AEI hierarchy_level 0 = detailed occupation (leaf)
COLUMNS = [
    "date_start",
    "geo_id",
    "category_name",
    "hierarchy_level",
    "metric_id",
    "value",
    "node_name",
    "node_external_id",
]


@dataclass(frozen=True)
class IngestResult:
    snapshot_ids: list[str]
    files: list[Path]


def download_release(dest_dir: Path = RAW_DIR, url: str = CSV_URL) -> Path:
    """Download the CSV into `dest_dir` unless it is already there."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / CSV_NAME
    if not target.exists():
        logger.info("downloading %s", url)
        urllib.request.urlretrieve(url, target)  # noqa: S310 (fixed https URL)
    return target


def read_finance_rows(csv_path: Path) -> list[AeiRow]:
    """Filter the AEI CSV to the geographies, occupations and metrics our snapshots use."""
    df = pd.read_csv(csv_path, usecols=COLUMNS, dtype=str)
    df = df[df["geo_id"].isin(GEOS)]
    soc_code = df["node_external_id"].str.removesuffix(".00")
    is_soc = (
        (df["category_name"] == "soc_occupation")
        & (df["hierarchy_level"] == DETAILED_OCCUPATION_LEVEL)
        & df["node_external_id"].str.endswith(".00", na=False)
        & soc_code.isin(FINANCE_SOC_CODES)
        & df["metric_id"].isin(SOC_METRICS)
    )
    is_overall = (df["category_name"] == "overall") & df["metric_id"].isin(OVERALL_METRICS)
    kept = df[is_soc | is_overall]
    return [
        AeiRow(
            period=str(row.date_start)[:7],
            geo=str(row.geo_id),
            category=str(row.category_name),
            metric=str(row.metric_id),
            value=float(str(row.value)),
            node_name=str(row.node_name),
            soc_code=str(row.node_external_id).removesuffix(".00")
            if row.category_name == "soc_occupation"
            else None,
        )
        for row in kept.itertuples(index=False)
    ]


def build_all(
    rows: list[AeiRow], triggers: list[ReviewTrigger], retrieved_at: str
) -> list[Snapshot]:
    """One snapshot per period, oldest first; each later one diffed against the one before."""
    snapshots: list[Snapshot] = []
    for period in sorted({r.period for r in rows}):
        previous = snapshots[-1] if snapshots else None
        snapshots.append(
            build_snapshot(rows, period, RELEASE_DATE, retrieved_at, previous, triggers)
        )
    return snapshots


def write_snapshots(snapshots: list[Snapshot], out_dir: Path = SNAPSHOT_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for snapshot in snapshots:
        path = out_dir / f"{snapshot.id}.json"
        text = json.dumps(snapshot.model_dump(), ensure_ascii=False, indent=2)
        path.write_text(text + "\n", encoding="utf-8")
        paths.append(path)
    return paths


def run_ingest(
    raw_dir: Path = RAW_DIR,
    out_dir: Path = SNAPSHOT_DIR,
    allow_download: bool = True,
    retrieved_at: str | None = None,
) -> IngestResult:
    """The whole pipeline; safe to run on a schedule (idempotent for the same release)."""
    csv_path = raw_dir / CSV_NAME
    if not csv_path.exists():
        if not allow_download:
            raise FileNotFoundError(f"{csv_path} missing; run without --offline to download it")
        csv_path = download_release(raw_dir)
    triggers = default_catalogue().assumptions_v1.review_triggers
    snapshots = build_all(
        read_finance_rows(csv_path), triggers, retrieved_at or date.today().isoformat()
    )
    files = write_snapshots(snapshots, out_dir)
    return IngestResult(snapshot_ids=[s.id for s in snapshots], files=files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="never download the raw CSV")
    parser.add_argument("--retrieved-at", default=None, help="override the retrieval date")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    result = run_ingest(allow_download=not args.offline, retrieved_at=args.retrieved_at)
    logger.info("wrote %s", ", ".join(str(p) for p in result.files))


if __name__ == "__main__":
    main()
