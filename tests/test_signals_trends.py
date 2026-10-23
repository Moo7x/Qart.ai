"""load_ai_trend: the job-board series once a region has enough history, otherwise the Indeed
tracker with the latest job-board figure; hiring_now breakdowns. Synthetic snapshot files."""

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.signals.trends import load_ai_trend, load_hiring_now

PULSE = {
    "source": "Indeed",
    "data_as_of": "2026-09-30",
    "caveats": [],
    "default_country": "AU",
    "countries": ["AU", "GB"],
    "events": [],
    "series": [
        {
            "country": c,
            "country_name": n,
            "series": "AI",
            "points": [{"month": "2026-09", "share_pct": 5.0}],
        }
        for c, n in (("AU", "Australia"), ("GB", "United Kingdom"))
    ],
}


def ats(weeks: int) -> dict[str, Any]:
    points = [
        {"period": f"2026-W{40 + i}", "total": 50, "ai": 20, "share_pct": 40.0}
        for i in range(weeks)
    ]
    return {
        "source": "ATS",
        "data_as_of": "2026-10-23",
        "first_snapshot": "2026-10-01",
        "caveats": ["c"],
        "min_sample": 20,
        "min_periods_for_chart": 4,
        "coverage": {"companies": ["A"]},
        "regions": [
            {"id": "global", "label": "All"},
            {"id": "malaysia_singapore", "label": "Malaysia + Singapore"},
        ],
        "series": [
            {"region": r, "granularity": "week", "points": points}
            for r in ("global", "malaysia_singapore")
        ],
        "skills_latest_week": [
            {
                "region": "malaysia_singapore",
                "skill_id": "python",
                "name": "Python",
                "mentions": 9,
                "total": 50,
                "share_pct": 18.0,
            },
            {
                "region": "malaysia_singapore",
                "skill_id": "rag",
                "name": "RAG",
                "mentions": 0,
                "total": 50,
                "share_pct": 0.0,
            },
        ],
        "families_latest_week": [
            {
                "region": "malaysia_singapore",
                "family": "analytics",
                "total": 25,
                "ai": 10,
                "share_pct": 40.0,
            }
        ],
    }


def write(tmp: Path, pulse: dict[str, Any] | None, ats_snapshot: dict[str, Any] | None) -> Path:
    if pulse:
        (tmp / "market_pulse.json").write_text(json.dumps(pulse))
    if ats_snapshot:
        (tmp / "ats_signals.json").write_text(json.dumps(ats_snapshot))
    return tmp


def test_job_boards_drive_the_chart_once_the_region_has_enough_weeks(tmp_path: Path) -> None:
    trend = load_ai_trend(directory=write(tmp_path, PULSE, ats(4)))
    assert trend["mode"] == "ats" and trend["region"] == "malaysia_singapore"
    assert [p["share_pct"] for p in trend["points"]] == [40.0] * 4 and trend[
        "fallback_reason"
    ] is None


def test_too_little_history_falls_back_to_indeed_with_todays_job_board_figure(
    tmp_path: Path,
) -> None:
    trend = load_ai_trend(directory=write(tmp_path, PULSE, ats(1)))
    assert trend["mode"] == "indeed" and trend["region_label"] == "Australia (not Malaysia)"
    assert trend["ats_latest"]["share_pct"] == 40.0 and trend["ats_latest"]["total"] == 50
    assert "switches to it after 4 weeks" in trend["fallback_reason"]


def test_without_job_board_data_the_indeed_tracker_is_used(tmp_path: Path) -> None:
    folder = write(tmp_path, PULSE, None)
    trend = load_ai_trend(directory=folder)
    assert trend["mode"] == "indeed" and trend["region"] == "AU" and trend["ats_latest"] is None
    assert load_ai_trend("GB", directory=folder)["region_label"] == "United Kingdom (not Malaysia)"
    assert load_hiring_now(directory=folder) is None


def test_hiring_now_lists_mentioned_skills_and_families(tmp_path: Path) -> None:
    view = load_hiring_now(directory=write(tmp_path, PULSE, ats(1)))
    assert view is not None and [s["skill_id"] for s in view["skills"]] == [
        "python"
    ]  # 0 mentions dropped
    assert view["families"][0]["family"] == "analytics"


def test_api_serves_the_trend_from_the_saved_snapshots(client: TestClient) -> None:
    body = client.get("/api/signals/ai-trend").json()
    assert body["mode"] in {"ats", "indeed"} and body["points"] and "stale" in body
    assert client.get("/api/signals/ai-trend?granularity=day").status_code == 422
    hiring = client.get("/api/signals/hiring-now").json()
    assert hiring["region"] == "malaysia_singapore" and hiring["skills"]
