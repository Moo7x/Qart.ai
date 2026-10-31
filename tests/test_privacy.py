"""A person can export and delete everything stored for them; idle profiles are deleted."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import update

from src import privacy
from src.agents import store
from src.journey.store import profile_table

PROFILE: dict[str, Any] = {
    "situation": "working",
    "current_role": "cash_application_analyst",
    "skills": {"reconciliation": {"level": 3, "evidence": "", "source": "self"}},
}


def test_every_person_table_has_a_profile_id_and_is_found() -> None:
    names = {t.name for t in privacy.person_tables()}
    expected = {"agent_run", "cv_version", "feedback", "journey_goal", "journey_progress"}
    assert expected <= names


def test_export_then_delete_removes_every_row(client: TestClient) -> None:
    pid = client.post("/api/profiles", json=PROFILE).json()["id"]
    client.put(f"/api/profiles/{pid}/progress", json={"done": [], "paused": True})
    engine = client.app.state.engine  # type: ignore[attr-defined]
    run = store.start(engine, "check", "reconciliation", pid, "test")
    store.step(engine, run, "think", "a step")
    exported = client.get(f"/api/profiles/{pid}/export").json()["tables"]
    assert exported["profile"][0]["id"] == pid
    assert exported["agent_run"] and exported["agent_step"] and exported["journey_progress"]
    deleted = client.delete(f"/api/profiles/{pid}").json()["deleted"]
    assert deleted["profile"] == 1 and deleted["agent_step"] == 1
    assert client.get(f"/api/profiles/{pid}").status_code == 404
    assert client.get(f"/api/profiles/{pid}/export").status_code == 404
    assert client.delete(f"/api/profiles/{pid}").status_code == 404


def test_only_idle_profiles_are_purged(client: TestClient) -> None:
    engine = client.app.state.engine  # type: ignore[attr-defined]
    idle = client.post("/api/profiles", json=PROFILE).json()["id"]
    active = client.post("/api/profiles", json=PROFILE).json()["id"]
    long_ago = (datetime.now(UTC) - timedelta(days=200)).replace(tzinfo=None)
    with engine.begin() as conn:
        conn.execute(
            update(profile_table).where(profile_table.c.id == idle).values(updated_at=long_ago)
        )
    assert privacy.purge_idle(engine, 90) == 1
    assert client.get(f"/api/profiles/{idle}").status_code == 404
    assert client.get(f"/api/profiles/{active}").status_code == 200
