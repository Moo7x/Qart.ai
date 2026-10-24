"""Opt-in real PostgreSQL onboarding regression and safe production diagnostics."""

import os
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.config import Settings
from tests.test_api_journey import NUR


def test_postgres_onboarding_and_destination(settings: Settings) -> None:
    url = os.environ.get("QART_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("set QART_TEST_POSTGRES_URL to a disposable local PostgreSQL database")
    app = create_app(replace(settings, database_url=url), first_run=False)
    try:
        with TestClient(app) as client:
            created = client.post("/api/profiles", json=NUR)
            assert created.status_code == 201, created.text
            pid = created.json()["id"]
            for scenario in ("moderate", "fast"):
                response = client.get(f"/api/profiles/{pid}/matches?scenario={scenario}")
                assert response.status_code == 200, response.text
                assert len(response.json()["roles"]) == 9
            chosen = client.post(
                f"/api/profiles/{pid}/destination", json={"role_id": "cost_accountant"}
            )
            assert chosen.status_code == 200
            assert client.get(f"/api/profiles/{pid}/pathway").status_code == 200
            assert client.get(f"/api/profiles/{pid}/future").status_code == 200
    finally:
        app.state.engine.dispose()


def test_error_reference_never_logs_exception_values(
    settings: Settings, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app(settings, first_run=False)

    def broken(*args: object) -> str:
        raise ValueError("private CV sentence and secret credential")

    monkeypatch.setattr("src.api.journey.create_profile", broken)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/api/profiles", json=NUR)
    assert response.status_code == 500 and "reference" in response.json()["detail"]
    assert "QART_REQUEST_ERROR" in caplog.text and "ValueError" in caplog.text
    assert "private CV sentence" not in caplog.text and "private-token" not in caplog.text
