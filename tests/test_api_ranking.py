"""GET /api/ranking/{user_id}: the role ranking with gaps, both scenarios and provenance."""

from fastapi.testclient import TestClient

LEVELS = {
    "spreadsheet_modelling": "sometimes",
    "financial_reporting": "sometimes",
    "recon_to_source": "confident",
    "sql_basics": "heard",
}


def set_answers(client: TestClient, **prefs: object) -> None:
    profile = client.get("/api/profile/u_aina").json()
    merged = {**profile.get("preferences", {}), "current_job": "reconciliation_associate", **prefs}
    assert client.post("/api/profile", json={**profile, "preferences": merged}).status_code == 200


def test_ranking_has_bands_gaps_scenarios_and_provenance(client: TestClient) -> None:
    set_answers(client, skill_levels=LEVELS, direction="adjacent", industry="Finance & accounting")
    body = client.get("/api/ranking/u_aina").json()
    assert body["scenario"] == "moderate" and not body["empty_profile"]
    assert set(body["scenarios"]) == {"moderate", "fast"}
    assert body["trend"]["data_as_of"] and "not predictions" in body["note"]
    top = body["roles"][0]
    assert top["band"] in {"Strong match", "Good match", "Stretch"}
    assert set(top["scenarios"]) == {"moderate", "fast"} and top["reasons"]
    assert top["family_name"] and top["components"]["skill"] > 0
    assert all({"label", "hours", "fits_timeframe"} <= set(g) for g in top["gap"])
    scores = [r["score"] for r in body["roles"]]
    assert scores == sorted(scores, reverse=True)
    evidence = [r["ai_use_evidence"] for r in body["roles"] if r["ai_use_evidence"]]
    assert evidence and all(e["automation_pct"] > 0 and e["period"] for e in evidence)


def test_fast_scenario_reorders_and_unknown_scenario_is_rejected(client: TestClient) -> None:
    set_answers(client, skill_levels=LEVELS, direction="adjacent")
    moderate = client.get("/api/ranking/u_aina?scenario=moderate").json()
    fast = client.get("/api/ranking/u_aina?scenario=fast").json()
    assert fast["scenario"] == "fast"
    by_id = {r["role_id"]: r for r in moderate["roles"]}
    for r in fast["roles"]:
        assert r["score"] == by_id[r["role_id"]]["scenarios"]["fast"]["score"]
    assert client.get("/api/ranking/u_aina?scenario=sideways").status_code == 422


def test_sparse_profile_gets_starter_roles(client: TestClient) -> None:
    set_answers(client, skill_levels={"customer_service": "sometimes"})
    body = client.get("/api/ranking/u_aina").json()
    assert body["empty_profile"] and body["roles"] == [] and body["message"]
    assert all(s["name"] for s in body["starter_roles"])
