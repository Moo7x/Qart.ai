"""Kavitha, the advanced persona: a labelled synthetic CV, served like the others."""

from pathlib import Path

from fastapi.testclient import TestClient

from src.config import Settings
from src.intake import extract as extract_mod
from src.pack import load_pack

KAVITHA = Path(__file__).parent.parent / "data" / "samples" / "kavitha.txt"


def test_kavitha_is_listed_and_served_as_a_synthetic_sample(client: TestClient) -> None:
    samples = {s["id"] for s in client.get("/api/pack").json()["samples"]}
    assert "kavitha" in samples
    text = client.get("/api/samples/kavitha").json()["text"]
    assert "THIS PERSON DOES NOT EXIST" in text
    for item in ("Power Automate", "Python scripts", "S/4HANA", "Power Query", "Train"):
        assert item in text


def test_kavitha_identifiers_are_removed_and_her_skills_are_read(settings: Settings) -> None:
    result = extract_mod.extract(load_pack(), KAVITHA.read_text(encoding="utf-8"), settings)
    assert result.removed.get("name") == 1
    skills = {s.skill for s in result.skills}
    assert {"erp", "reporting", "dashboards", "process_automation"} <= skills
    erp = next(s for s in result.skills if s.skill == "erp")
    assert "S/4HANA" in erp.evidence
