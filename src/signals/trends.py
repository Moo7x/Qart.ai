"""The one data-loading function behind the AI trend chart: `load_ai_trend`.

Two real sources, both read from saved snapshots (the app never calls the internet):
  ats     public ATS job boards (Greenhouse, Lever, Ashby): share of open postings that mention
          AI, weekly or monthly, by region (Malaysia, Singapore, APAC, remote, global)
  indeed  Indeed Hiring Lab AI Tracker: monthly AI share of postings for 9 countries (not Malaysia)
ATS history starts with the first snapshot, so the chart uses it only once a region has at least
`min_periods_for_chart` periods with enough postings. Until then it shows the Indeed series and
reports the latest ATS figure for the region next to it (`ats_latest`), with the reason.
"""

import json
from pathlib import Path
from typing import Any

from src.signals.pipeline import MARKET_PULSE, SNAPSHOT_DIR

ATS_SNAPSHOT = "ats_signals.json"
DEFAULT_ATS_REGION = "malaysia_singapore"


def _read(directory: Path, name: str) -> dict[str, Any] | None:
    path = directory / name
    if not path.exists():
        return None
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data


def _ats_series(ats: dict[str, Any], region: str, granularity: str) -> list[dict[str, Any]]:
    for s in ats.get("series", []):
        if s["region"] == region and s["granularity"] == granularity:
            return [p for p in s["points"]]
    return []


def _meta(snapshot: dict[str, Any], keys: tuple[str, ...]) -> dict[str, Any]:
    return {k: snapshot.get(k) for k in keys}


META_KEYS = (
    "source",
    "license",
    "attribution",
    "update_frequency",
    "data_as_of",
    "fetched_at",
    "caveats",
)


def load_ai_trend(
    region: str | None = None, granularity: str = "week", directory: Path = SNAPSHOT_DIR
) -> dict[str, Any]:
    """The AI-share series for `region` (an ATS region id or an Indeed country code)."""
    ats, pulse = _read(directory, ATS_SNAPSHOT), _read(directory, MARKET_PULSE)
    ats_regions = [r["id"] for r in (ats or {}).get("regions", [])]
    labels = {r["id"]: r["label"] for r in (ats or {}).get("regions", [])}
    countries = (pulse or {}).get("countries", [])
    if region is None:
        region = (
            DEFAULT_ATS_REGION
            if DEFAULT_ATS_REGION in ats_regions
            else (pulse or {}).get("default_country")
        )

    options = {
        "ats_regions": [
            {
                "id": r,
                "label": labels[r],
                "periods_with_data": sum(
                    p["share_pct"] is not None for p in _ats_series(ats or {}, r, granularity)
                ),
            }
            for r in ats_regions
        ],
        "indeed_countries": [
            {
                "id": c,
                "label": next(
                    (s.get("country_name") for s in pulse["series"] if s["country"] == c), c
                ),
            }
            for c in countries
        ]
        if pulse
        else [],
    }
    ats_latest = None
    if ats and region is not None and region in ats_regions:
        points = _ats_series(ats, region, granularity)
        usable = [p for p in points if p["share_pct"] is not None]
        latest = points[-1] if points else None
        if latest:
            ats_latest = {
                **latest,
                "region": region,
                "label": labels[region],
                "data_as_of": ats.get("data_as_of"),
            }
        need = int(ats.get("min_periods_for_chart", 4))
        if len(usable) >= need:
            return {
                "mode": "ats",
                "region": region,
                "region_label": labels[region],
                "granularity": granularity,
                "points": [
                    {"period": p["period"], "share_pct": p["share_pct"], "total": p["total"]}
                    for p in points
                ],
                "meta": {
                    **_meta(ats, META_KEYS),
                    "first_snapshot": ats.get("first_snapshot"),
                    "coverage": ats.get("coverage"),
                },
                "ats_latest": ats_latest,
                "fallback_reason": None,
                "options": options,
            }
        fallback_reason: str | None = (
            f"Job-board history for {labels[region]} starts {ats.get('first_snapshot')}; "
            f"the chart switches to it after {need} {granularity}s with at least "
            f"{ats.get('min_sample')} postings "
            f"(now {len(usable)}). Until then it shows the Indeed tracker."
        )
        indeed_region = pulse.get("default_country") if pulse else None
    else:
        no_ats = "No job-board snapshot yet; showing the Indeed tracker."
        fallback_reason = None if ats else no_ats
        indeed_region = region if region in countries else (pulse or {}).get("default_country")

    if not pulse:
        return {
            "mode": "none",
            "region": region,
            "points": [],
            "meta": None,
            "ats_latest": ats_latest,
            "fallback_reason": "No trend snapshot available.",
            "options": options,
        }
    series = next((s for s in pulse["series"] if s["country"] == indeed_region), None)
    name = (series or {}).get("country_name", indeed_region)
    return {
        "mode": "indeed",
        "region": indeed_region,
        "region_label": f"{name} (not Malaysia)",
        "granularity": "month",
        "points": [
            {"period": p["month"], "share_pct": p["share_pct"], "total": None}
            for p in (series or {}).get("points", [])
        ],
        "meta": _meta(pulse, META_KEYS) | {"events": pulse.get("events", [])},
        "ats_latest": ats_latest,
        "fallback_reason": fallback_reason,
        "options": options,
    }


def load_hiring_now(
    region: str = DEFAULT_ATS_REGION, directory: Path = SNAPSHOT_DIR
) -> dict[str, Any] | None:
    """Latest-week skill shares and AI share per role family for a region (ATS), or None."""
    ats = _read(directory, ATS_SNAPSHOT)
    if not ats:
        return None
    labels = {r["id"]: r["label"] for r in ats.get("regions", [])}
    skills = sorted(
        (
            s
            for s in ats.get("skills_latest_week", [])
            if s["region"] == region and s["mentions"] > 0
        ),
        key=lambda s: (-(s["share_pct"] or 0), s["name"]),
    )
    families = [f for f in ats.get("families_latest_week", []) if f["region"] == region]
    return {
        "region": region,
        "region_label": labels.get(region, region),
        "skills": skills,
        "families": families,
        "meta": _meta(ats, META_KEYS)
        | {"coverage": ats.get("coverage"), "min_sample": ats.get("min_sample")},
    }
