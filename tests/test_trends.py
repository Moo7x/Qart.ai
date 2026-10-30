"""Trend series keep the long and recent windows apart and label skills by their basis."""

from fastapi.testclient import TestClient

from src.evidence.trends import trends
from src.match.engine import Evidence
from src.pack import load_pack


def share_rows() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for year in range(2011, 2026):
        clerical = 15.0 - 0.2 * (year - 2011) + (0.4 * (year - 2021) if year > 2021 else 0)
        for entity, value in (("overall", 100.0), ("clerical", clerical)):
            rows.append(
                {
                    "source_id": "dosm_wages_occupation",
                    "series": "employees",
                    "entity": entity,
                    "geography": "MYS",
                    "period": str(year),
                    "value": value,
                }
            )
    return rows


def test_long_and_recent_change_can_point_different_ways() -> None:
    evidence = Evidence(
        automation_share={"13-2011.00": 45.0}, automation_period="", automation_source="t"
    )
    out = trends(load_pack(), share_rows(), evidence)
    clerical = next(g for g in out["employment"] if g["group"] == "clerical")
    assert clerical["change_long"] < 0 < clerical["change_recent"]
    assert clerical["major_group"] == "4"
    names = {s["name"]: s for s in out["skills"]}
    assert names["General Ledger Accounting"]["change"] < 0  # routine skill: less emphasis
    assert all(s["change"] == 0 for s in out["skills"] if s["ai_role"] == "neutral")


def test_fast_adoption_moves_skill_weights_further_than_moderate() -> None:
    evidence = Evidence(
        automation_share={"13-2011.00": 45.0}, automation_period="2026-05", automation_source="t"
    )
    out = trends(load_pack(), share_rows(), evidence)
    moderate = {s["skill"]: s["change"] for s in out["skills_by_scenario"]["moderate"]}
    fast = {s["skill"]: s["change"] for s in out["skills_by_scenario"]["fast"]}
    assert out["skills"] == out["skills_by_scenario"]["fast"]  # the existing field is unchanged
    assert all(abs(fast[k]) >= abs(moderate[k]) for k in fast)
    assert out["evidence_period"] == "2026-05"


def test_trends_route(client: TestClient) -> None:
    body = client.get("/api/trends").json()
    assert set(body) == {
        "employment",
        "recent_from",
        "job_ads",
        "skills",
        "skills_by_scenario",
        "evidence_period",
        "evidence_source",
        "exposure",
    }
