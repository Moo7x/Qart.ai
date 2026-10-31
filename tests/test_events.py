"""Progress events (C5): B's routes record what the person did, and only when something changed."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from src.journey.events import list_events, record_event


def _engine(client: TestClient) -> Engine:
    return client.app.state.engine  # type: ignore[attr-defined,no-any-return]


def _kinds(client: TestClient, pid: str) -> list[tuple[str, str]]:
    return [(e["kind"], e["ref"]) for e in list_events(_engine(client), pid)]


def test_profile_routes_record_level_changes_with_their_source(client: TestClient) -> None:
    body = {
        "situation": "working",
        "skills": {"erp": {"level": 2, "source": "cv", "evidence": "SAP"}},
    }
    pid = client.post("/api/profiles", json=body).json()["id"]
    first = list_events(_engine(client), pid)
    assert [(e["kind"], e["ref"], e["before"], e["after"]) for e in first] == [
        ("level_changed", "erp", None, {"level": 2, "source": "cv"})
    ]
    client.put(f"/api/profiles/{pid}", json=body)  # nothing changed: no new event
    assert len(list_events(_engine(client), pid)) == 1
    body["skills"]["erp"]["level"] = 3
    client.put(f"/api/profiles/{pid}", json=body)
    client.post(f"/api/profiles/{pid}/answer", json={"skill": "reporting", "level": 2})
    events = list_events(_engine(client), pid)[1:]
    assert [(e["ref"], e["before"], e["after"]) for e in events] == [
        ("erp", 2, {"level": 3, "source": "cv"}),
        ("reporting", None, {"level": 2, "source": "self"}),
    ]


def test_destination_and_progress_routes_record_events(client: TestClient) -> None:
    pid = client.post("/api/profiles", json={"situation": "working"}).json()["id"]
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": "cost_accountant"})
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": "cost_accountant"})  # same
    path = client.get(f"/api/profiles/{pid}/pathway").json()
    course, step = path["steps"][0]["course"]["id"], path["practice_steps"][0]["id"]
    client.put(f"/api/profiles/{pid}/progress", json={"done": [course], "skipped": [step]})
    client.put(f"/api/profiles/{pid}/progress", json={"done": [course]})  # nothing new
    client.put(f"/api/profiles/{pid}/progress", json={"done": []})
    assert _kinds(client, pid) == [
        ("destination_chosen", "cost_accountant"),
        ("course_done", course),
        ("step_skipped", step),
        ("course_undone", course),
    ]


def test_unknown_kind_is_rejected(client: TestClient) -> None:
    with pytest.raises(ValueError, match="unknown event kind"):
        record_event(_engine(client), "p", "promoted", "x")
