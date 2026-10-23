"""Skills Radar routes: shapes, provenance, staleness and the per-person view (no network)."""

from datetime import date

from fastapi.testclient import TestClient

from src.api_signals import freshness


def test_market_pulse_and_skills_carry_provenance(client: TestClient) -> None:
    for path in ("/api/signals/market-pulse", "/api/signals/skills"):
        body = client.get(path).json()
        for key in ("source", "source_url", "license", "attribution", "data_as_of", "fetched_at"):
            assert body[key], (path, key)
        assert body["caveats"] and isinstance(body["stale"], bool)
    pulse = client.get("/api/signals/market-pulse").json()
    assert pulse["attribution"] == "Source: Indeed Hiring Lab"
    assert pulse["covers_malaysia"] is False and "not Malaysia" in pulse["default_country_label"]


def test_staleness_uses_the_data_date() -> None:
    assert freshness("2026-10-01", date(2026, 10, 20)) == {"age_days": 19, "stale": False}
    assert freshness("2026-08-01", date(2026, 10, 20))["stale"] is True
    assert freshness("not a date")["stale"] is True


def test_for_user_links_profile_tools_and_says_it_changes_nothing(client: TestClient) -> None:
    profile = client.get("/api/profile/u_aina").json()
    before = client.get("/api/path/u_aina").json()
    prefs = {**profile.get("preferences", {}), "tools": ["Python", "SQL", "Excel", "None of these"]}
    client.post("/api/profile", json={**profile, "preferences": prefs})
    view = client.get("/api/signals/for-user/u_aina").json()
    mine = {s["id"]: s for s in view["user_skills"]}
    assert {"python", "sql_basics", "spreadsheet_modelling"} <= set(mine)
    assert mine["python"]["why"] == "you use Python"
    assert all(s["id"] not in mine for s in view["rising_skills_not_held"])
    assert "not a forecast" in view["note"] and view["no_market_data"] == []
    assert client.get("/api/path/u_aina").json()["steps"] == before["steps"]  # informational only
