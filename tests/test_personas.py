"""Four synthetic personas get visibly different results: the proof that nothing is hard-coded (B6).

Each persona is built through the API from fixed levels (no model), each claim quoting a
sentence of their synthetic CV in data/samples/. The test also checks that every number in the
C2 role score and the C3 plan carries a source or a label (docs/PHASE2_PLAN.md §4).
"""

import re
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src import params

MEI_CASH = (
    "Counted and reconciled the daily cash and card takings against the point-of-sale system."
)
NUR_SAP = (
    "Applied incoming customer receipts to open invoices in SAP "
    "for four entities, about 1,200 lines a month."
)
KAVITHA_FLOWS = (
    "Built Power Automate flows that read supplier invoices from a "
    "shared mailbox and log them for AP review."
)
KAVITHA_BI = (
    "Built multi-source Power BI dashboards with Power Query, "
    "combining SAP, Excel and payroll data."
)
# skill: (level, the CV sentence behind it). Situation as the person states it.
HAFIZ = {
    "variance_analytics": (
        1,
        "Final-year project: variance analysis of a manufacturing company's standard costs.",
    ),
    "standard_costing": (
        1,
        "Final-year project: variance analysis of a manufacturing company's standard costs.",
    ),
    "accounting_principles": (
        2,
        "Courses in financial accounting, management accounting, auditing and taxation.",
    ),
    "database_querying": (
        1,
        "Learned SQL basics and built simple dashboards in Power BI for a class project.",
    ),
    "dashboards": (
        1,
        "Learned SQL basics and built simple dashboards in Power BI for a class project.",
    ),
    "internal_controls": (
        2,
        "Helped prepare working papers and tested internal controls over purchases.",
    ),
    "invoice_processing": (2, "Matched supplier invoices to purchase orders and delivery notes."),
}
MEI = {
    "reconciliation": (
        2,
        MEI_CASH,
    ),
    "vendor_management": (
        2,
        "Managed stock orders with suppliers and checked deliveries against invoices.",
    ),
    "invoice_processing": (
        1,
        "Managed stock orders with suppliers and checked deliveries against invoices.",
    ),
    "reporting": (2, "Prepared the weekly sales report for the area manager."),
    "stakeholder_management": (2, "Trained and scheduled a team of eight staff."),
}
NUR = {
    "cash_application": (
        3,
        NUR_SAP,
    ),
    "reconciliation": (
        3,
        "Reconciled daily bank statements to the cash ledger and cleared unapplied cash.",
    ),
    "credit_collections": (
        3,
        "Worked with the credit team on overdue accounts and collection follow-ups.",
    ),
    "erp": (
        2,
        NUR_SAP,
    ),
    "reporting": (2, "Built the daily cash position report in Excel for the AR manager."),
    "accounting_principles": (2, "Prepared monthly ageing reports."),
}
UAT = "Ran user acceptance testing for the S/4HANA migration of the general ledger and reporting."
PACK_REPORT = (
    "Prepared the monthly management reporting pack and variance commentary for regional finance "
    "leads."
)
KAVITHA = {
    "process_automation": (
        3,
        KAVITHA_FLOWS,
    ),
    "reporting": (4, "Train and review the work of new reporting analysts joining the team."),
    "dashboards": (
        3,
        KAVITHA_BI,
    ),
    "data_validation": (3, "Checked data quality of ledger extracts before reporting."),
    "data_management": (3, "Checked data quality of ledger extracts before reporting."),
    "financial_reporting": (3, PACK_REPORT),
    "variance_analytics": (3, PACK_REPORT),
    "general_ledger": (3, "Prepared month-end journals and balance sheet reconciliations in SAP."),
    "accounting_principles": (
        3,
        "Prepared month-end journals and balance sheet reconciliations in SAP.",
    ),
    "erp": (3, UAT),
    "financial_systems": (3, UAT),
    "data_migration": (2, UAT),
}
PERSONAS = {
    "hafiz": ("student", HAFIZ),
    "mei": ("switcher", MEI),
    "nur": ("working", NUR),
    "kavitha": ("working", KAVITHA),
}


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


# --- Every number in C2 and C3 carries a source or a label ---------------------------------------
# Each numeric field (as a path pattern) and the check that its label is present.


def _requirement(card: dict[str, Any], skill: str) -> dict[str, Any]:
    return next(r for r in card["requirements"] if r["skill"] == skill)


C2_LABELS: list[tuple[str, Any]] = [
    (r"fit", lambda card, _: card["band_basis"] == "assumption" and card["components"]),
    (r"fit_range\.(low|high)", lambda card, _: card["fit_range"]["basis"]),
    (
        r"components\[(\d+)\]\.weight",
        lambda card, m: _requirement(card, card["components"][int(m[1])]["skill"])["shift_reason"],
    ),
    (r"components\[(\d+)\]\.points", lambda card, _: card["band_basis"]),
    (r"components\[(\d+)\]\.claimed", lambda card, m: card["components"][int(m[1])]["source"]),
    (r"components\[(\d+)\]\.required", lambda card, _: True),  # TalentCorp tier level, cited pages
    (r"raise\[(\d+)\]\.points", lambda card, m: card["raise"][int(m[1])]["via"]),
    (r"raise\[(\d+)\]\.(from_level|to_level)", lambda card, m: card["raise"][int(m[1])]["via"]),
    (r"pay\.\w+", lambda card, _: card["pay"]["kind"] == "observed" and card["pay"]["source"]),
]
C3_LABELS: list[tuple[str, Any]] = [
    (
        r"steps\[(\d+)\]\.time\.(value|low|high)",
        lambda p, m: p["steps"][int(m[1])]["time"]["basis"],
    ),
    (r"steps\[(\d+)\]\.(order|target_level)", lambda p, _: True),  # positions and levels
    (
        r"practice_steps\[(\d+)\]\.time\.(value|low|high)",
        lambda p, m: p["practice_steps"][int(m[1])]["time"]["basis"] == "practice_estimate",
    ),
    (
        r"practice_steps\[(\d+)\]\.week_start\.(low|high)",
        lambda p, m: p["practice_steps"][int(m[1])]["time"]["basis"] == "practice_estimate",
    ),
    (r"practice_steps\[(\d+)\]\.(order|target_level)", lambda p, _: True),
    (r"study_hours", lambda p, _: all(s["time"]["basis"] for s in p["steps"])),
    (r"practice_weeks\.(low|high)", lambda p, _: p["practice_weeks"]["kind"] == "estimate"),
    (
        r"fit_after_(study|practice)\.(low|high)",
        lambda p, m: p[f"fit_after_{m[1]}"]["kind"] == "estimate",
    ),
    (r"free_share", lambda p, _: p["free_share_basis"]),
]
C2_FIELDS = ("fit", "fit_range", "band", "components", "raise", "essentials_short", "pay")
C3_STEP_FIELDS = ("order", "target_level", "time")
C3_TOTALS = (
    "practice_steps",
    "study_hours",
    "practice_weeks",
    "fit_after_study",
    "fit_after_practice",
    "free_share",
)


def _numbers(value: Any, path: str = "") -> list[str]:
    if isinstance(value, bool) or value is None:
        return []
    if isinstance(value, int | float):
        return [path]
    if isinstance(value, dict):
        return [n for k, v in value.items() for n in _numbers(v, f"{path}.{k}" if path else k)]
    if isinstance(value, list):
        return [n for i, v in enumerate(value) for n in _numbers(v, f"{path}[{i}]")]
    return []


def _unlabelled(doc: dict[str, Any], numbers: list[str], table: list[tuple[str, Any]]) -> list[str]:
    missing = []
    for path in numbers:
        for pattern, label in table:
            match = re.fullmatch(pattern, path)
            if match:
                if not label(doc, match):
                    missing.append(path)
                break
        else:
            missing.append(path)  # a number with no declared label
    return missing


def test_every_c2_and_c3_number_carries_a_source_or_a_label(results: dict[str, Any]) -> None:
    for persona, r in results.items():
        card, path = r["top"], r["pathway"]
        c2 = _numbers({k: card[k] for k in C2_FIELDS})
        c3 = _numbers({k: path[k] for k in C3_TOTALS}) + _numbers(
            {"steps": [{k: s[k] for k in C3_STEP_FIELDS} for s in path["steps"]]}
        )
        assert c2 and c3
        assert _unlabelled(card, c2, C2_LABELS) == [], persona
        assert _unlabelled(path, c3, C3_LABELS) == [], persona
