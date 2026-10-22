"""Contract check on real endpoint output: every field in a contract example is present in the
corresponding API response (extra optional fields are allowed; see CONTRACT_QUESTIONS Q2)."""

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.engine import params
from tests.helpers import golden_journey_raw

EXAMPLES = Path(__file__).resolve().parent.parent / "schemas" / "examples"


def example(name: str) -> Any:
    return json.loads((EXAMPLES / f"{name}.json").read_text(encoding="utf-8"))


def missing_keys(expected: Any, actual: Any, path: str = "") -> list[str]:
    """Keys present in the example but absent in the output (recursing into first list items)."""
    missing: list[str] = []
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, value in expected.items():
            if key not in actual:
                missing.append(f"{path}.{key}")
            else:
                missing += missing_keys(value, actual[key], f"{path}.{key}")
    elif isinstance(expected, list) and isinstance(actual, list) and expected and actual:
        missing += missing_keys(expected[0], actual[0], f"{path}[0]")
    return missing


def setup_journey(client: TestClient) -> None:
    for event in golden_journey_raw()["events"]:
        client.post("/api/events", json=event)
    client.post("/api/ingest/run")


def test_skill_state_output_has_every_contract_field(client: TestClient) -> None:
    setup_journey(client)
    states = client.get("/api/skills/u_aina").json()
    state = next(s for s in states if s["skill_id"] == "unsupported_adjustment")
    assert missing_keys(example("skill_state"), state) == []


def test_recommendation_output_has_every_contract_field(client: TestClient) -> None:
    setup_journey(client)
    rec = client.get("/api/recommendations/u_aina?scenario=agentic").json()
    assert missing_keys(example("recommendation"), rec) == []
    assert all(r["formula"] == params.SCORE_FORMULA for r in rec["roles"])


def test_path_role_snapshot_assumption_profile_outputs(client: TestClient) -> None:
    setup_journey(client)
    assert missing_keys(example("path_plan"), client.get("/api/path/u_aina").json()) == []
    assert missing_keys(example("role"), client.get("/api/roles").json()[0]) == []
    assert missing_keys(example("snapshot"), client.get("/api/snapshots").json()[-1]) == []
    assumptions = client.get("/api/assumptions").json()
    assert missing_keys(example("company_assumptions"), assumptions) == []
    assert missing_keys(example("profile"), client.get("/api/profile/u_aina").json()) == []


def test_contract_example_event_is_accepted(client: TestClient) -> None:
    response = client.post("/api/events", json=example("event"))
    assert response.status_code == 200, response.text
