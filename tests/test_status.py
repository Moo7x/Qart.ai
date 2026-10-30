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
