"""Thin profile: ranked roles, fit 0 with a range, and a plan. Unknown skills are named."""

from fastapi.testclient import TestClient

from src.pack import load_pack

# Every onboarding question skipped: only the situation is required.
THIN = {"situation": "student"}


def _thin(client: TestClient) -> str:
    response = client.post("/api/profiles", json=THIN)
    assert response.status_code == 201
    return str(response.json()["id"])


def test_thin_profile_gets_every_role_at_fit_0_with_a_range_and_a_plan(
    client: TestClient,
) -> None:
    pid = _thin(client)
    roles = client.get(f"/api/profiles/{pid}/matches").json()["roles"]
    assert len(roles) == len(load_pack().destination_roles)
    for role in roles:
        assert role["fit"] == 0.0
        assert role["fit_range"]["low"] == 0.0
        assert role["fit_range"]["high"] > 0.0
    assert any(role["effort_hours"] > 0 for role in roles)  # a plan exists for the roles


def test_thin_profile_gets_a_pathway_and_tracks(client: TestClient) -> None:
    pid = _thin(client)
    top = client.get(f"/api/profiles/{pid}/matches").json()["roles"][0]["role_id"]
    assert client.post(f"/api/profiles/{pid}/destination", json={"role_id": top}).status_code == 200
    path = client.get(f"/api/profiles/{pid}/pathway").json()
    assert path["fit_before"] == 0.0
    assert path["steps"] or path["uncovered"]
    assert client.get(f"/api/profiles/{pid}/tracks").status_code == 200


def test_unknown_skill_gives_422_with_its_name(client: TestClient) -> None:
    bad = {**THIN, "skills": {"quantum_ledger": {"level": 2}}}
    response = client.post("/api/profiles", json=bad)
    assert response.status_code == 422
    assert "quantum_ledger" in response.json()["detail"]

    pid = _thin(client)
    answer = client.post(
        f"/api/profiles/{pid}/answer", json={"skill": "quantum_ledger", "level": 2}
    )
    assert answer.status_code == 422
    assert "quantum_ledger" in answer.json()["detail"]

    whatif = client.post(f"/api/profiles/{pid}/whatif", json={"changes": {"quantum_ledger": 2}})
    assert whatif.status_code == 422
    assert "quantum_ledger" in whatif.json()["detail"]
