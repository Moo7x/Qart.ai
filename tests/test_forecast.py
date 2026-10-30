"""Forecasts are chosen by backtest against keeping the last value, and say so when nothing wins."""

import json
import math
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src import params
from src.collectors import dosm_wages
from src.evidence import forecast as fc
from src.evidence.store import Observation
from src.match.evidence import automation_evidence
from src.pack import load_pack

FIXTURES = Path(__file__).parent / "fixtures"
FETCHED = datetime(2026, 10, 23, tzinfo=UTC)


def as_rows(observations: list[Observation]) -> list[dict[str, Any]]:
    return [{**o.__dict__, "fetched_at": FETCHED} for o in observations]


def wage_rows() -> list[dict[str, Any]]:
    raw = json.loads((FIXTURES / "dosm_wages_occupation_full.json").read_text(encoding="utf-8"))
    return as_rows(dosm_wages.parse(raw))


def points(values: list[float]) -> list[tuple[str, float]]:
    return [(str(2011 + i), v) for i, v in enumerate(values)]


def test_naive_is_kept_when_no_model_beats_it() -> None:
    def forecaster(method: str, history: list[float], steps: int) -> float:
        return history[-1] if method == "naive" else history[-1] + 5.0  # every model is worse

    entry = fc.forecast_series(
        "s",
        "employment_share",
        "t",
        points([10.0 + 0.1 * (i % 2) for i in range(14)]),
        "src",
        None,
        forecaster,
        ("naive", "linear", "damped"),
    )
    assert entry["model"] == "naive" and "No model beat" in entry["note"]
    assert entry["forecast"][0]["point"] == 10.1


def test_a_steady_trend_is_forecast_by_a_trend_model_with_an_interval() -> None:
    values = [10.0 + 0.3 * i + (0.05 if i % 3 == 0 else -0.05) for i in range(15)]
    entry = fc.forecast_series(
        "s", "employment_share", "t", points(values), "src", None, fc._local, fc.LOCAL_METHODS
    )
    assert entry["model"] != "naive" and entry["backtest"]["ratio"] < 1.0
    one, two = entry["forecast"]
    assert one["period"] == "2026" and two["period"] == "2027"
    assert two["point"] > values[-1]  # the trend continues
    for f in entry["forecast"]:
        assert f["low"] is not None and f["low"] <= f["point"] <= f["high"]


def test_too_few_points_give_no_forecast_and_say_why() -> None:
    entry = fc.forecast_series(
        "s", "job_ads", "t", points([1.0, 2.0, 3.0]), "src", None, fc._local, fc.LOCAL_METHODS
    )
    assert entry["forecast"] == [] and entry["model"] is None and "too few" in entry["note"]


def test_quarter_labels_roll_over_the_year() -> None:
    assert fc._next_period("2025-Q4", 1) == "2026-Q1"
    assert fc._next_period("2026-Q2", 2) == "2026-Q4"


def test_employment_forecasts_from_real_dosm_rows_use_the_global_model_too() -> None:
    entries = {e["series_id"]: e for e in fc.employment_forecasts(wage_rows())}
    clerical = entries["employment_share:clerical"]
    assert clerical["label"] == "estimate" and len(clerical["forecast"]) == len(
        params.FORECAST_HORIZONS
    )
    assert "gbr" in clerical["backtest"]["ratios"]  # scored like every other model
    assert all(math.isfinite(f["point"]) for f in clerical["forecast"])
    assert clerical["history"][-1]["period"] == "2025"


def test_job_ads_are_counted_only_after_the_last_coverage_break() -> None:
    rows = []
    for i, (quarter, total) in enumerate(
        [("2024-Q1", 100.0), ("2024-Q2", 105.0), ("2024-Q3", 260.0), ("2024-Q4", 265.0)]
    ):
        rows.append(
            {
                "source_id": "dosm_job_market_insights",
                "series": "online_job_offerings",
                "entity": "all occupations",
                "period": quarter,
                "value": total,
                "fetched_at": FETCHED,
                "id": i,
            }
        )
    total = next(e for e in fc.job_ad_forecasts(rows) if e["series_id"] == "job_ads:total")
    assert [h["period"] for h in total["history"]] == ["2024-Q3", "2024-Q4"]
    assert "2024-Q3" in total["note"] and total["forecast"] == []


def test_outlooks_keep_demand_and_ai_use_apart() -> None:
    rows = wage_rows()
    pack = load_pack()
    entries = fc.forecasts(pack, rows, automation_evidence(rows))
    skills = [e for e in entries if e["kind"] == "skill_outlook"]
    roles = [e for e in entries if e["kind"] == "role_outlook"]
    assert roles and all("not for the role itself" in r["note"] for r in roles)
    assert skills and all(
        {"demand_change_pp", "ai_use_share"} <= set(s["components"]) for s in skills
    )
    assert all("automated" not in s["title"].lower() for s in skills)


def test_forecast_route_returns_labelled_estimates(client: TestClient) -> None:
    body = client.get("/api/forecast").json()
    assert isinstance(body, list)
    assert all(entry["label"] == "estimate" for entry in body)
