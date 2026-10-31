"""The change test reruns the real engine on test evidence values and never stores anything."""

from typing import Any

from fastapi.testclient import TestClient

from src.pack import load_pack

PROFILE: dict[str, Any] = {
    "situation": "working",
    "current_role": "cash_application_analyst",
    "weekly_hours": 6,
    "skills": {
        "reconciliation": {"level": 3, "evidence": "", "source": "self"},
        "reporting": {"level": 2, "evidence": "", "source": "self"},
    },
}


def _role_with_both_kinds() -> tuple[str, str, str, str]:
    """A destination role with a non-essential routine skill and a non-essential AI-complement."""
    pack = load_pack()
    for role in pack.destination_roles.values():
        kinds = {pack.skills[r.skill].ai_role: r.skill for r in role.requires if not r.essential}
        if "routine" in kinds and "complement" in kinds:
            return role.id, role.soc, kinds["routine"], kinds["complement"]
    raise AssertionError("the pack has no role with both kinds of skill")


def test_a_higher_automation_share_moves_weights_both_ways(client: TestClient) -> None:
    role_id, soc, routine, complement = _role_with_both_kinds()
    profile = client.post("/api/profiles", json=PROFILE).json()["id"]
    client.post(f"/api/profiles/{profile}/destination", json={"role_id": role_id})
    before_obs = client.get("/api/observations").json()
    body = client.post(
        f"/api/profiles/{profile}/evidence-test",
        json={
            "scenario": "fast",
            "overrides": [{"kind": "occupation_share", "key": soc, "value": 80}],
        },
    ).json()
    assert body["label"] == "Test value, not real data"
    moved = {w["skill"]: w for w in body["weights"] if w["role_id"] == role_id}
    assert moved[routine]["after"] < moved[routine]["before"]  # routine work loses weight
    assert moved[complement]["after"] > moved[complement]["before"]  # complementing work gains
    pack = load_pack()
    essentials = {r.skill for r in pack.destination_roles[role_id].requires if r.essential}
    assert not essentials & set(moved)  # essentials never shift
    assert body["pathway"]["role_id"] == role_id
    assert client.get("/api/observations").json() == before_obs  # nothing stored


def test_unknown_keys_are_refused(client: TestClient) -> None:
    profile = client.post("/api/profiles", json=PROFILE).json()["id"]
    response = client.post(
        f"/api/profiles/{profile}/evidence-test",
        json={"overrides": [{"kind": "task_share", "key": "999999", "value": 50}]},
    )
    assert response.status_code == 422 and "999999" in response.json()["detail"]


def test_values_outside_0_to_100_are_refused(client: TestClient) -> None:
    profile = client.post("/api/profiles", json=PROFILE).json()["id"]
    _, soc, _, _ = _role_with_both_kinds()
    response = client.post(
        f"/api/profiles/{profile}/evidence-test",
        json={"overrides": [{"kind": "occupation_share", "key": soc, "value": 140}]},
    )
    assert response.status_code == 422
