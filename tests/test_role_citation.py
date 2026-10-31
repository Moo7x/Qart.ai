"""A role's expert outlook cites the study pages that name that role, not a fixed page range."""

from fastapi.testclient import TestClient

from src.pack import load_pack


def test_role_cards_and_tasks_cite_each_roles_own_pages(client: TestClient) -> None:
    body = {"situation": "working", "skills": {"accounting_principles": {"level": 3}}}
    pid = client.post("/api/profiles", json=body).json()["id"]
    pack = load_pack()
    for card in client.get(f"/api/profiles/{pid}/matches").json()["roles"]:
        expert = next(o for o in card["outlook"] if o["kind"] == "expert")
        assert expert["source"] == pack.destination_roles[card["role_id"]].study_source
    tax = client.get(f"/api/profiles/{pid}/roles/tax_analyst/tasks").json()
    assert tax["sources"]["expert"].endswith("PDF p. 22, 26, 50")
