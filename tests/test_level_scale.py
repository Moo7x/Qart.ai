"""The 0–5 scale: six labels on the API, stored levels keep their numbers, level 5 is accepted."""

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from src import params
from src.config import Settings
from src.intake import extract as extract_mod
from src.journey.store import ProfileData
from src.levels import load_levels
from src.match.engine import Evidence, score_role
from src.pack import load_pack

NUR = (Path(__file__).parent.parent / "data" / "samples" / "nur.txt").read_text(encoding="utf-8")
LABELS = ["none", "novice", "aware", "working", "proficient", "expert"]


def test_api_exposes_six_labels_and_the_level_sentences(client: TestClient) -> None:
    body = client.get("/api/pack").json()
    assert body["proficiency"] == LABELS
    levels = body["levels"]
    assert [s["label"] for s in levels["scale"]] == LABELS
    assert levels["rules"]
    erp = levels["skills"]["erp"]
    assert sorted(erp["anchors"]) == ["1", "2", "3", "4", "5"]
    assert erp["basis"] and erp["status"] == "draft"


def test_a_stored_level_4_claim_still_loads_and_scores_the_same() -> None:
    stored = {"situation": "working", "skills": {"erp": {"level": 4, "source": "cv"}}}
    data = ProfileData.model_validate(stored)
    assert data.levels() == {"erp": 4}
    pack = load_pack()
    role = pack.destination_roles["finance_systems_analyst"]
    evidence = Evidence(automation_share={}, automation_period="", automation_source="")
    # Requirement numbers are unchanged, so a level at or above the need still counts in full.
    erp = next(
        r
        for r in score_role(pack, role, data.levels(), "moderate", evidence).requirements
        if r.skill == "erp"
    )
    assert erp.claimed == 4 and erp.contribution > 0


def test_level_5_is_accepted_on_a_profile_and_as_an_answer(client: TestClient) -> None:
    body = {"situation": "working", "skills": {"erp": {"level": 5, "source": "self"}}}
    created = client.post("/api/profiles", json=body)
    assert created.status_code == 201
    pid = created.json()["id"]
    answer = client.post(f"/api/profiles/{pid}/answer", json={"skill": "reporting", "level": 5})
    assert answer.status_code == 200
    too_high = client.post(f"/api/profiles/{pid}/answer", json={"skill": "reporting", "level": 6})
    assert too_high.status_code == 422


def test_extraction_schema_accepts_5_and_keeps_such_a_claim(settings: Settings) -> None:
    schema = extract_mod.schema(load_pack())
    assert schema["properties"]["skills"]["items"]["properties"]["level"]["enum"] == [1, 2, 3, 4, 5]
    claim = {
        "skill": "cash_application",
        "level": 5,
        "evidence": "Applied incoming customer receipts",
    }

    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        assert "5 = expert" in messages[0]["content"]  # the scale meanings reach the model
        return json.dumps(
            {"current_role": "other", "years_experience": 6, "skills": [claim], "interests": []}
        )

    result = extract_mod.extract(load_pack(), NUR, settings, complete)
    assert [(s.skill, s.level) for s in result.skills if s.skill != "erp"] == [
        ("cash_application", 5)
    ]


def test_level_guide_falls_back_to_meanings_over_the_budget() -> None:
    guide = extract_mod.level_guide(load_levels())
    assert len(guide) <= params.LEVEL_GUIDE_MAX_CHARS
    assert all(s.meaning in guide for s in load_levels().scale if s.level)
