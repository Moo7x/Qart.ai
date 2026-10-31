"""Every page shows the same plan for a person: one context (src/journey/person.py) builds it."""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.api.journey import load_personas

PERSONAS = load_personas()


def _profile(client: TestClient, name: str) -> str:
    persona = PERSONAS[name]
    skills = {
        k: {"level": c["level"], "evidence": c["evidence"], "source": "cv"}
        for k, c in persona["skills"].items()
    }
    body = {"situation": persona["situation"], "skills": skills}
    pid: str = client.post("/api/profiles", json=body).json()["id"]
    return pid


def _get(client: TestClient, path: str) -> Any:
    response = client.get(path)
    assert response.status_code == 200, (path, response.text)
    return response.json()


@pytest.mark.parametrize("name", sorted(PERSONAS))
def test_matches_pathway_sdg_tracks_and_future_share_one_plan(
    client: TestClient, name: str
) -> None:
    pid = _profile(client, name)
    roles = _get(client, f"/api/profiles/{pid}/matches")["roles"]
    card = min(roles, key=lambda r: r["fit"])  # the furthest role: a plan with real steps
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": card["role_id"]})
    path = _get(client, f"/api/profiles/{pid}/pathway")
    assert path["steps"] or path["practice_steps"]

    assert card["effort_hours"] == path["total_hours"]
    assert card["uncovered"] == path["uncovered"]

    sdg = _get(client, f"/api/profiles/{pid}/sdg")
    assert {r["skill"] for r in sdg["rows"]} <= set(path["study_levels"])
    assert {c for r in sdg["rows"] for c in r["steps"]} <= {s["id"] for s in path["steps"]}

    comparison = _get(client, f"/api/profiles/{pid}/tracks")["comparison"]
    assert comparison["with_ai"]["plan_hours"] == path["total_hours"]
    if not path["ai_basics"]["shown"]:  # skipped AI basics add no hours to the with-AI route
        assert comparison["with_ai"]["ai_basics_hours"] == 0

    future = _get(client, f"/api/profiles/{pid}/future")["scenarios"]["moderate"]
    assert (future["hours"], future["uncovered"]) == (path["total_hours"], path["uncovered"])
