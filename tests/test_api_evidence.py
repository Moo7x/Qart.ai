"""Evidence routes return sources with terms, sourced signals, and protect Run now."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from src.api import evidence as evidence_api
from src.collectors import talentcorp
from src.evidence.store import finish_run, insert_observations, start_run


def engine_of(client: TestClient) -> Engine:
    engine: Engine = client.app.state.engine  # type: ignore[attr-defined]
    return engine


def seed(client: TestClient) -> None:
    engine = engine_of(client)
    run_id = start_run(engine, "test")
    new = insert_observations(engine, talentcorp.parse(talentcorp.load_extraction()), run_id)
    finish_run(
        engine,
        run_id,
        "changed",
        new,
        [{"source_id": "talentcorp_gbs_2024", "status": "ok", "new": new, "note": "test"}],
    )


def test_sources_list_terms_and_latest_status(client: TestClient) -> None:
    seed(client)
    body = client.get("/api/sources").json()
    talent = next(s for s in body if s["id"] == "talentcorp_gbs_2024")
    assert talent["observations"] > 0
    assert talent["last_status"] == "ok"
    assert all(s["terms"] and s["does_not_show"] for s in body)


def test_signals_carry_sources_and_cited_evidence(client: TestClient) -> None:
    seed(client)
    body = client.get("/api/signals").json()
    assert body["observations"] > 0
    for signal in body["signals"]:
        assert signal["sources"] and signal["evidence"]
        assert all(e["cited_span"] for e in signal["evidence"])


def test_empty_database_gives_empty_signals_not_an_error(client: TestClient) -> None:
    assert client.get("/api/signals").json()["signals"] == []


def test_unknown_source_is_404(client: TestClient) -> None:
    assert client.get("/api/observations", params={"source_id": "nope"}).status_code == 404


def test_run_now_requires_the_admin_token(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(evidence_api, "run_pipeline", lambda *args: calls.append(args))
    assert client.post("/api/pipeline/run").status_code == 403
    assert client.post("/api/pipeline/run", headers={"X-Admin-Token": "wrong"}).status_code == 403
    response = client.post("/api/pipeline/run", headers={"X-Admin-Token": "test-admin-token"})
    assert response.status_code == 202
    assert calls and calls[0][1] == "admin"


def test_runs_are_listed_newest_first(client: TestClient) -> None:
    seed(client)
    seed(client)
    runs = client.get("/api/pipeline/runs").json()
    assert [r["id"] for r in runs] == [2, 1]
    assert runs[0]["status"] == "changed"
