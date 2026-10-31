"""Four synthetic personas get visibly different results: the proof that nothing is hard-coded (B6).

Each persona is built through the API from fixed levels (no model), each claim quoting a
sentence of their synthetic CV in data/samples/. The test also checks that every number in the
C2 role score and the C3 plan carries a source or a label (docs/PHASE2_PLAN.md §4).
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient

from src import params
from src.api.journey import load_personas
from src.match.labels import C2_LABELS, C3_LABELS, c2_numbers, c3_numbers, unlabelled

# persona: (situation, {skill: (level, the CV sentence behind it)}), from data/samples/personas.yaml
PERSONAS = {
    name: (p["situation"], {k: (c["level"], c["evidence"]) for k, c in p["skills"].items()})
    for name, p in load_personas().items()
}
KAVITHA = PERSONAS["kavitha"][1]


def journey(client: TestClient, persona: str) -> dict[str, Any]:
    """One persona through the API: profile → matches → top role chosen → pathway and tracks."""
    situation, claims = PERSONAS[persona]
    text = client.get(f"/api/samples/{persona}").json()["text"]
    skills = {}
    for skill, (level, quote) in claims.items():
        assert quote in text, f"{persona}: quote not in the sample CV"
        skills[skill] = {"level": level, "evidence": quote, "source": "cv"}
    created = client.post("/api/profiles", json={"situation": situation, "skills": skills})
    assert created.status_code == 201
    pid = created.json()["id"]
    matches = client.get(f"/api/profiles/{pid}/matches").json()
    top = matches["roles"][0]
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": top["role_id"]})
    return {
        "pid": pid,
        "claims": claims,
        "top": top,
        "pathway": client.get(f"/api/profiles/{pid}/pathway").json(),
        "tracks": client.get(f"/api/profiles/{pid}/tracks").json(),
    }


@pytest.fixture
def results(client: TestClient) -> dict[str, dict[str, Any]]:
    out = {p: journey(client, p) for p in PERSONAS}
    for r in out.values():  # every persona really produces a role and a plan (no vacuous checks)
        assert r["top"]["fit"] > 0
        assert r["pathway"]["steps"] or r["pathway"]["practice_steps"]
    return out


def test_top_roles_differ_between_at_least_three_personas(results: dict[str, Any]) -> None:
    assert len({r["top"]["role_id"] for r in results.values()}) >= 3


def test_kavithas_top_fit_exceeds_nurs(results: dict[str, Any]) -> None:
    assert results["kavitha"]["top"]["fit"] > results["nur"]["top"]["fit"]


def test_ai_basics_for_hafiz_and_not_for_kavitha(results: dict[str, Any]) -> None:
    for persona, shown in (("hafiz", True), ("kavitha", False)):
        assert results[persona]["pathway"]["ai_basics"]["shown"] is shown
        basics = next(t for t in results[persona]["tracks"]["tracks"] if t["id"] == "ai_basics")
        assert basics["shown"] is shown


def test_kavitha_gets_practice_wherever_a_core_skill_is_short(
    client: TestClient, results: dict[str, Any]
) -> None:
    """Practice appears for every role where a core skill is below its level; her top role,
    whose core skills she already meets, honestly has none (team decision, B6)."""
    kavitha = results["kavitha"]
    pid = kavitha["pid"]
    at_two = {s for s, (level, _) in KAVITHA.items() if level >= params.NO_BEGINNER_FROM_LEVEL}
    roles = client.get(f"/api/profiles/{pid}/matches").json()["roles"]
    short = [
        r
        for r in roles
        if any(
            q["tier"] == "core" and (q["claimed"] or 0) < q["required"] for q in r["requirements"]
        )
    ]
    assert short  # the check below runs on real cases
    for role in short:
        path = client.get(f"/api/profiles/{pid}/pathway?role_id={role['role_id']}").json()
        assert path["practice_steps"], role["role_id"]
        for step in path["steps"]:
            assert not (step["course"]["level"] == "beginner" and step["skill"] in at_two)
    if kavitha["top"]["role_id"] not in {r["role_id"] for r in short}:
        assert kavitha["pathway"]["practice_steps"] == []


def test_every_c2_and_c3_number_carries_a_source_or_a_label(results: dict[str, Any]) -> None:
    for persona, r in results.items():
        card, path = r["top"], r["pathway"]
        c2, c3 = c2_numbers(card), c3_numbers(path)
        assert c2 and c3
        assert unlabelled(card, c2, C2_LABELS) == [], persona
        assert unlabelled(path, c3, C3_LABELS) == [], persona
