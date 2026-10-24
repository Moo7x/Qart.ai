"""A pasted posting is read with quote checks; coverage counts this posting, never readiness."""

import json
from typing import Any

from fastapi.testclient import TestClient

from src.config import Settings
from src.goal.posting import POSTING_DEFAULT_LEVEL, coverage, read_requirements, stepping_stones
from src.match.engine import Evidence
from src.pack import load_pack
from tests.test_api_journey import create

POSTING = """Finance Systems Analyst (synthetic posting for tests)
Contact: recruiter.sample@example.com
- Must have strong knowledge of accounting principles and general ledger.
- Experience configuring ERP systems such as SAP S/4HANA is required.
- Build dashboards in Power BI for month-end reporting.
- Fluent in Japanese is a plus.
"""
EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="test")


def model(items: list[dict[str, Any]]) -> Any:
    def complete(messages: list[dict[str, str]], schema: dict[str, Any]) -> str:
        assert "recruiter.sample@example.com" not in messages[1]["content"]  # scrubbed first
        return json.dumps({"requirements": items})

    return complete


def test_quotes_not_in_the_posting_are_rejected_and_other_stays_unmapped(
    settings: Settings,
) -> None:
    items = [
        {
            "quote": "Must have strong knowledge of accounting principles",
            "skill": "accounting_principles",
            "essential": True,
            "level": None,
        },
        {
            "quote": "Experience configuring ERP systems such as SAP S/4HANA is required",
            "skill": "erp",
            "essential": True,
            "level": 3,
        },
        {
            "quote": "Fluent in Japanese is a plus",
            "skill": "other",
            "essential": False,
            "level": None,
        },
        {"quote": "Ten years of Python experience", "skill": "sql", "essential": True, "level": 4},
    ]
    check = read_requirements(load_pack(), POSTING, settings, model(items))
    assert check.rejected == 1 and len(check.requirements) == 3 and "gpt-4o-mini" in check.engine
    result = coverage(check, {"accounting_principles": 3, "erp": 2})
    assert (result["covered"], result["mapped"], result["outside_catalogue"]) == (1, 2, 1)
    assert (result["essentials_met"], result["essentials"]) == (1, 2)  # ERP needs 3, claimed 2
    assert [r["status"] for r in result["requirements"]] == ["met", "below", "outside_catalogue"]


def test_keyword_fallback_is_labelled_and_marks_required_lines(settings: Settings) -> None:
    check = read_requirements(load_pack(), POSTING, settings)
    assert check.engine == "BM25 keywords (fallback)" and check.requirements
    assert any(r.essential for r in check.requirements)
    result = coverage(check, {})
    assert result["covered"] == 0 and result["not_stated"] == result["mapped"]
    assert result["default_level"] == POSTING_DEFAULT_LEVEL


def test_stepping_stones_share_the_posting_skills(settings: Settings) -> None:
    items = [
        {
            "quote": "Experience configuring ERP systems such as SAP S/4HANA is required",
            "skill": "erp",
            "essential": True,
            "level": None,
        }
    ]
    check = read_requirements(load_pack(), POSTING, settings, model(items))
    coverage(check, {})
    stones = stepping_stones(load_pack(), check, {}, "moderate", EVIDENCE)
    assert stones and all("Enterprise Resource Planning (ERP)" in s["shared"] for s in stones)
    assert any(s["shared_courses"] for s in stones)  # learning that serves both


def test_goal_routes(client: TestClient) -> None:
    pid = create(client)
    assert client.get(f"/api/profiles/{pid}/goal").json() == {"goal": None}
    body = {
        "role_title": "Finance Systems Analyst",
        "company": "Example GBS",
        "posting_text": POSTING,
    }
    saved = client.put(f"/api/profiles/{pid}/goal", json=body).json()
    assert saved["goal"]["company"] == "Example GBS" and saved["coverage"]["mapped"] > 0
    assert client.get(f"/api/profiles/{pid}/goal").json()["coverage"] == saved["coverage"]
    bare = client.put(f"/api/profiles/{pid}/goal", json={"role_title": "Analyst"}).json()
    assert bare["coverage"] is None and bare["stepping_stones"] == []
