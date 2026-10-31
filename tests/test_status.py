"""The status page reports measured usage, labels cost as an estimate and never invents a zero."""

from fastapi.testclient import TestClient

from src import params
from src.api.status import cost_rows


def test_cost_uses_declared_prices_and_leaves_unknown_prices_empty() -> None:
    rows = cost_rows(
        [
            {
                "purpose": "cv_extraction",
                "engine": "openai",
                "model": "gpt-4o-mini",
                "calls": 2,
                "failed": 0,
                "tokens_in": 1_000_000,
                "tokens_out": 0,
                "seconds": 3.0,
            },
            {
                "purpose": "runpod_embed",
                "engine": "runpod",
                "model": "BAAI/bge-m3",
                "calls": 1,
                "failed": 0,
                "tokens_in": 0,
                "tokens_out": 0,
                "seconds": 2.0,
            },
        ]
    )
    assert rows[0]["cost_usd"] == params.PRICES_PER_MILLION_TOKENS["gpt-4o-mini"]["in"]
    if params.RUNPOD_USD_PER_SECOND is None:
        assert rows[1]["cost_usd"] is None  # no declared GPU price: no made-up number


def test_status_route_shape(client: TestClient) -> None:
    body = client.get("/api/status").json()
    assert {"sources", "runs", "engines", "usage", "cost", "fairness", "platform_sdg"} <= set(body)
    assert body["cost"]["label"] == "estimate"
    assert body["engines"]["language_model"]["configured"] is False  # tests run offline


def test_fairness_result_is_shown_with_its_date(client: TestClient) -> None:
    fairness = client.get("/api/status").json()["fairness"]
    assert fairness["available"] and fairness["identical"] is True
    assert fairness["pairs"] >= 1 and fairness["checked_at"]


def test_platform_sdg_totals_are_withheld_below_five_people(client: TestClient) -> None:
    def add_person() -> None:
        profile = {"situation": "working", "skills": {"reconciliation": {"level": 2}}}
        pid = client.post("/api/profiles", json=profile).json()["id"]
        client.post(f"/api/profiles/{pid}/destination", json={"role_id": "cost_accountant"})

    for _ in range(params.PLATFORM_SDG_MIN_PROFILES - 1):
        add_person()
    below = client.get("/api/status").json()["platform_sdg"]
    assert below["suppressed"] is True and below["totals"] == []
    add_person()
    shown = client.get("/api/status").json()["platform_sdg"]
    assert shown["suppressed"] is False and shown["profiles"] == params.PLATFORM_SDG_MIN_PROFILES
    assert shown["totals"] and all(t["hours"] >= 0 for t in shown["totals"])
