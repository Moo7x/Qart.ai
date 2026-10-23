"""Live proposals are persisted, profile-scoped and cannot silently replace an accepted journey."""

from typing import cast

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from src import params
from src.changes.service import refresh_proposals
from src.changes.store import list_changes
from src.collectors.base import CollectorResult
from src.evidence.store import Observation, insert_observations, query_observations
from src.pipeline import run as pipeline
from tests.test_api_journey import NUR, create
from tests.test_changes import rows


def add(engine: Engine, value: float, period: str = "2026-04") -> None:
    row = rows(value, period)[0]
    row["series"] = str(row["series"])
    insert_observations(engine, [Observation(**row)], run_id=None)


def prepared(client: TestClient) -> tuple[Engine, str]:
    engine: Engine = cast(FastAPI, client.app).state.engine
    add(engine, 20)
    profile_id = create(client)
    client.post(
        f"/api/profiles/{profile_id}/destination", json={"role_id": "o2c_reporting_analyst"}
    )
    return engine, profile_id


def current_fits(client: TestClient, profile_id: str) -> dict[str, float]:
    body = client.get(f"/api/profiles/{profile_id}/matches?scenario=fast").json()
    return {r["role_id"]: r["fit"] for r in body["roles"]}


def test_pipeline_publication_keeps_accepted_results_until_user_accepts(client: TestClient) -> None:
    engine, profile_id = prepared(client)
    saved_before = client.get(f"/api/profiles/{profile_id}").json()
    old = current_fits(client, profile_id)
    add(engine, 80, "2026-05")
    refresh_proposals(engine, previous_cutoff=1, run_id=None)
    assert current_fits(client, profile_id) == old
    response = client.get(f"/api/profiles/{profile_id}/changes").json()
    assert len(response["proposals"]) == 2
    proposal = next(p for p in response["proposals"] if p["scenario"] == "fast")
    assert proposal["actionable"] and proposal["report"]["recommendation_changed"]
    accepted = client.post(
        f"/api/profiles/{profile_id}/changes/{proposal['id']}", json={"decision": "accept"}
    )
    assert accepted.status_code == 200
    assert current_fits(client, profile_id) != old
    saved = client.get(f"/api/profiles/{profile_id}").json()
    assert saved == saved_before
    assert saved["destination"] == "o2c_reporting_analyst"


def test_decline_and_reruns_do_not_recreate_proposals(client: TestClient) -> None:
    engine, profile_id = prepared(client)
    before = current_fits(client, profile_id)
    add(engine, 80, "2026-05")
    response = client.get(f"/api/profiles/{profile_id}/changes").json()
    proposal = response["proposals"][0]
    url = f"/api/profiles/{profile_id}/changes/{proposal['id']}"
    assert client.post(url, json={"decision": "decline"}).status_code == 200
    refresh_proposals(engine, previous_cutoff=1)
    refreshed = client.get(f"/api/profiles/{profile_id}/changes").json()
    assert len(refreshed["proposals"]) == 2
    assert (
        next(p for p in refreshed["proposals"] if p["id"] == proposal["id"])["status"] == "declined"
    )
    assert current_fits(client, profile_id) == before


def test_other_profile_cannot_resolve_proposal_and_changed_context_is_stale(
    client: TestClient,
) -> None:
    engine, profile_id = prepared(client)
    other = create(client)
    add(engine, 80, "2026-05")
    proposal = client.get(f"/api/profiles/{profile_id}/changes").json()["proposals"][0]
    assert (
        client.post(
            f"/api/profiles/{other}/changes/{proposal['id']}", json={"decision": "accept"}
        ).status_code
        == 404
    )
    client.put(f"/api/profiles/{profile_id}", json={**NUR, "weekly_hours": 2})
    assert (
        client.post(
            f"/api/profiles/{profile_id}/changes/{proposal['id']}", json={"decision": "accept"}
        ).status_code
        == 409
    )


def test_replay_is_read_only_and_reports_real_period_choices(client: TestClient) -> None:
    engine, profile_id = prepared(client)
    add(engine, 80, "2026-05")
    fits = current_fits(client, profile_id)
    before = client.get(f"/api/profiles/{profile_id}").json()
    query = "source_id=anthropic_economic_index&before=2026-04&after=2026-05&scenario=fast"
    response = client.get(f"/api/profiles/{profile_id}/changes/replay?{query}")
    assert response.status_code == 200
    assert response.json()["mode"] == "replay"
    assert response.json()["evidence"][0]["after"] == 80
    assert client.get(f"/api/profiles/{profile_id}").json() == before
    assert current_fits(client, profile_id) == fits
    bad = client.get(
        f"/api/profiles/{profile_id}/changes/replay?{query.replace('2026-04', '2025-01')}"
    )
    assert bad.status_code == 422
    assert client.get("/api/profiles/unknown/changes").status_code == 404


def test_cutoff_reconstructs_prior_value_when_source_revises_a_fact(client: TestClient) -> None:
    engine, _ = prepared(client)
    cutoff = query_observations(engine)[0]["id"]
    add(engine, 70)
    assert query_observations(engine, through_id=cutoff)[0]["value"] == 20
    assert query_observations(engine)[0]["value"] == 70


def test_scheduled_run_publishes_without_a_page_request(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, profile_id = prepared(client)
    collectors = {key: (lambda client, state: CollectorResult([])) for key in pipeline.COLLECTORS}
    collectors["aei"] = lambda client, state: CollectorResult(
        [Observation(**rows(80, "2026-05")[0])]
    )
    monkeypatch.setattr(pipeline, "COLLECTORS", collectors)
    result = pipeline.run_pipeline(
        engine,
        "schedule",
        client_factory=lambda: httpx.Client(
            transport=httpx.MockTransport(lambda r: httpx.Response(500))
        ),
        retry_pause=0,
    )
    assert result.status == "changed"
    stored = list_changes(engine, profile_id)
    assert len(stored) == 2
    assert all(p["run_id"] == result.run_id for p in stored)


def test_changed_calculation_policy_invalidates_an_old_proposal(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine, profile_id = prepared(client)
    add(engine, 80, "2026-05")
    proposal = client.get(f"/api/profiles/{profile_id}/changes").json()["proposals"][0]
    monkeypatch.setattr(params, "CALCULATION_VERSION", "test-new-policy")
    response = client.post(
        f"/api/profiles/{profile_id}/changes/{proposal['id']}", json={"decision": "accept"}
    )
    assert response.status_code == 409
