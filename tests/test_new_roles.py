"""B10: Tax Analyst is fully wired: sourced, ranked with components, pay and an SDG row."""

from fastapi.testclient import TestClient

from src.evidence.field import field_profile
from src.pack import load_pack

ROLE = "tax_analyst"


def test_tax_analyst_is_sourced_and_followed_by_the_evidence_layer() -> None:
    pack = load_pack()
    role = pack.destination_roles[ROLE]
    assert 50 in role.pages and role.impact == "low"
    assert any(r.essential for r in role.requires)
    assert field_profile().occupation(role.soc) is not None
    assert pack.tasks.occupations[role.soc].skills["tax_preparation"]
    assert pack.sdg.roles[ROLE]


def test_tax_analyst_appears_in_matches_with_components_pay_and_sdg(client: TestClient) -> None:
    body = {"situation": "working", "skills": {"accounting_principles": {"level": 3}}}
    pid = client.post("/api/profiles", json=body).json()["id"]
    matches = client.get(f"/api/profiles/{pid}/matches").json()
    card = next(r for r in matches["roles"] if r["role_id"] == ROLE)
    assert card["components"] and card["band"]
    assert card["pay"] is None  # not published until the wage series is collected
    assert card["listed_transition"] is False
    assert any(r["role_id"] == ROLE for r in matches["sdg_roles"])
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": ROLE})
    path = client.get(f"/api/profiles/{pid}/pathway").json()
    assert "Tax Preparation" in path["uncovered"]  # Green Tax Strategies: UN CC:Learn course
    rows = {r["skill"] for r in client.get(f"/api/profiles/{pid}/sdg").json()["rows"]}
    assert "green_tax_strategies" in rows
