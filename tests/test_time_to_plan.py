"""Time to roles and a plan is measured from the intake timer and the destination choice."""

from fastapi.testclient import TestClient


def make(client: TestClient, intake_seconds: float | None) -> None:
    body = {"situation": "working", "skills": {"reporting": {"level": 2}}}
    if intake_seconds is not None:
        body["intake_seconds"] = intake_seconds
    pid = client.post("/api/profiles", json=body).json()["id"]
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": "cost_accountant"})


def test_time_to_plan_counts_only_timed_intakes_with_a_destination(client: TestClient) -> None:
    make(client, 120.0)
    make(client, 600.0)
    make(client, None)  # an edit or an API-made profile: not timed, not counted
    measured = client.get("/api/status").json()["time_to_plan"]
    assert measured["people"] == 2 and measured["under_target"] == 1
    assert measured["target_seconds"] == 300 and measured["kind"] == "observed"
