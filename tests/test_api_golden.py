"""Behaviour guard for refactors: the API answers for the four personas match a stored snapshot.

The snapshot (tests/golden/api_personas.json) is what the app answered when it was last
regenerated on purpose. A refactor that changes any answer fails here. When a change is meant to
alter answers, regenerate and review the diff:

    UPDATE_GOLDEN=1 python -m pytest tests/test_api_golden.py
"""

import json
import os
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src.api.journey import load_personas

GOLDEN = Path(__file__).parent / "golden" / "api_personas.json"
ROUTES = ("matches", "pathway", "tracks", "sdg", "badges", "future", "radar")
VOLATILE = {"earned_at", "id"}  # times and random ids differ on every run


def _stable(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _stable(v) for k, v in value.items() if k not in VOLATILE}
    if isinstance(value, list):
        return [_stable(v) for v in value]
    return value


def _answers(client: TestClient) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, persona in sorted(load_personas().items()):
        skills = {
            k: {"level": c["level"], "evidence": c["evidence"], "source": "cv"}
            for k, c in persona["skills"].items()
        }
        body = {"situation": persona["situation"], "skills": skills}
        pid = client.post("/api/profiles", json=body).json()["id"]
        top = client.get(f"/api/profiles/{pid}/matches").json()["roles"][0]["role_id"]
        client.post(f"/api/profiles/{pid}/destination", json={"role_id": top})
        out[name] = {
            route: _stable(client.get(f"/api/profiles/{pid}/{route}").json()) for route in ROUTES
        }
    return out


def test_persona_answers_match_the_snapshot(client: TestClient) -> None:
    answers = _answers(client)
    if os.environ.get("UPDATE_GOLDEN"):
        GOLDEN.parent.mkdir(exist_ok=True)
        GOLDEN.write_text(json.dumps(answers, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    stored = json.loads(GOLDEN.read_text(encoding="utf-8"))
    for name in answers:
        for route in ROUTES:
            assert answers[name][route] == stored[name][route], f"{name} /{route} changed"
