"""The plan adapts to the person (B5): AI basics, beginner courses and straight-to-practice."""

from fastapi.testclient import TestClient

from src import params
from src.journey.store import SkillClaim
from src.match.engine import Evidence, rank_roles
from src.pack import load_pack
from src.pathway.planner import ai_basics_choice, plan_pathway

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")
POWER_AUTOMATE = (
    "Built Power Automate flows that read supplier invoices from a shared mailbox and log them "
    "for AP review."
)
UAT = "Ran user acceptance testing for the S/4HANA migration of the general ledger and reporting."
# Kavitha (data/samples/kavitha.txt) at fixed levels, each quoting her synthetic CV.
KAVITHA = {
    "process_automation": (3, POWER_AUTOMATE),
    "reporting": (4, "Train and review the work of new reporting analysts joining the team."),
    "dashboards": (
        3,
        "Built multi-source Power BI dashboards with Power Query, combining SAP, "
        "Excel and payroll data.",
    ),
    "data_validation": (3, "Checked data quality of ledger extracts before reporting."),
    "financial_reporting": (
        3,
        "Prepared the monthly management reporting pack and variance "
        "commentary for regional finance leads.",
    ),
    "general_ledger": (3, "Prepared month-end journals and balance sheet reconciliations in SAP."),
    "erp": (3, UAT),
    "financial_systems": (3, UAT),
    "data_migration": (2, UAT),
}


def kavitha(evidenced: bool = True) -> dict[str, SkillClaim]:
    return {
        k: SkillClaim(
            level=level, evidence=quote if evidenced else "", source="cv" if evidenced else "self"
        )
        for k, (level, quote) in KAVITHA.items()
    }


def _plans(claims: dict[str, SkillClaim], situation: str):  # type: ignore[no-untyped-def]
    pack = load_pack()
    levels = {k: c.level for k, c in claims.items()}
    return [
        plan_pathway(pack, m, levels, 6, "moderate", EVIDENCE, claims, situation)
        for m in rank_roles(pack, levels, "moderate", EVIDENCE)
    ]


def test_kavitha_skips_ai_basics_and_gets_no_beginner_course_for_her_skills() -> None:
    claims = kavitha()
    for path in _plans(claims, "working"):
        assert path.ai_basics["shown"] is False
        assert POWER_AUTOMATE in path.ai_basics["reason"]
        assert any(a["rule"] == "ai_basics_skipped" for a in path.adjustments)
        at_two = {k for k, c in claims.items() if (c.level or 0) >= params.STUDY_MAX_LEVEL}
        for step in path.steps:
            assert not (step.course.level == "beginner" and step.skill in at_two), step.course.id


def test_removing_kavithas_evidence_brings_ai_basics_back() -> None:
    for path in _plans(kavitha(evidenced=False), "working"):
        assert path.ai_basics["shown"] is True


def test_students_and_switchers_always_see_ai_basics() -> None:
    pack = load_pack()
    for situation in params.AI_BASICS_ALWAYS:
        assert ai_basics_choice(pack, kavitha(), situation)["shown"] is True


def test_a_skill_at_the_study_maximum_goes_straight_to_practice() -> None:
    pack = load_pack()
    role = pack.destination_roles["o2c_reporting_analyst"]
    core = next(r for r in role.requires if r.tier == "core")
    claims = {core.skill: SkillClaim(level=2, evidence="Did it at work.", source="cv")}
    path = next(p for p in _plans(claims, "working") if p.role_id == role.id)
    assert all(s.skill != core.skill for s in path.steps)
    assert [p.target_level for p in path.practice_steps if p.skill == core.skill] == [3]
    name = pack.skills[core.skill].name
    assert any(a["rule"] == "straight_to_practice" and name in a["text"] for a in path.adjustments)


def test_hafiz_sees_ai_basics_first_through_the_api(client: TestClient) -> None:
    body = {"situation": "student", "skills": {"accounting_principles": {"level": 1}}}
    pid = client.post("/api/profiles", json=body).json()["id"]
    top = client.get(f"/api/profiles/{pid}/matches").json()["roles"][0]["role_id"]
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": top})
    tracks = client.get(f"/api/profiles/{pid}/tracks").json()
    first = tracks["tracks"][0]
    assert first["id"] == "ai_basics" and first["shown"] is True and first["nodes"]
    assert tracks["comparison"]["with_ai"]["ai_basics_hours"] > 0
