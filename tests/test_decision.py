"""Decision support: meters keep meanings apart, questions and plans follow declared rules."""

from fastapi.testclient import TestClient

from src.match.decision import best_questions, fit_range, meters, sensitivity, what_if
from src.match.engine import Evidence, score_role
from src.pack import load_pack
from src.pathway.optimise import compare_plans
from tests.test_api_journey import create

EVIDENCE = Evidence(
    automation_share={
        "15-2051.01": 66.0,
        "13-2011.00": 45.0,
        "15-1211.00": 84.0,
        "13-2031.00": 34.0,
        "13-1111.00": 45.0,
        "13-1023.00": 66.0,
    },
    automation_period="2026-05",
    automation_source="test",
)
LEVELS: dict[str, int | None] = {"reporting": 2, "dashboards": 1, "erp": 2}


def test_meters_separate_unstated_essentials_from_confirmed_gaps() -> None:
    pack = load_pack()
    match = score_role(pack, pack.destination_roles["budget_analyst"], LEVELS, "moderate", EVIDENCE)
    m = meters(match)
    assert m["essentials_unstated"] == [
        "Budget Management",
        "Financial Planning, Analysis and Forecasting",
    ]
    assert m["essentials_below"] == [] and m["essentials_ready"] is False
    assert 0 < m["completeness"] < 100 and m["stated"] == 1


def test_fit_range_spans_unstated_skills_and_is_exact_when_all_known() -> None:
    pack = load_pack()
    role = pack.destination_roles["o2c_reporting_analyst"]
    match = score_role(pack, role, LEVELS, "moderate", EVIDENCE)
    r = fit_range(pack, match, LEVELS, "moderate", EVIDENCE)
    assert r["low"] == match.fit < r["high"]
    known = {req.skill: 2 for req in role.requires}
    full = score_role(pack, role, known, "moderate", EVIDENCE)
    assert fit_range(pack, full, known, "moderate", EVIDENCE) == {"low": full.fit, "high": full.fit}


def test_best_questions_are_unstated_and_ranked_by_declared_value() -> None:
    pack = load_pack()
    found = best_questions(pack, LEVELS, "moderate", EVIDENCE, None, "budget_analyst")
    assert 0 < len(found) <= 3
    assert all(q.skill not in LEVELS for q in found)
    assert [q.value for q in found] == sorted((q.value for q in found), reverse=True)
    assert {q.skill for q in found[:2]} == {"budget_management", "fpa"}  # the goal's essentials
    assert all("essential for Budget Analyst" in q.effect for q in found[:2])


def test_sensitivity_and_what_if_leave_inputs_unchanged() -> None:
    pack = load_pack()
    before = dict(LEVELS)
    s = sensitivity(pack, LEVELS, "moderate", EVIDENCE, None)
    assert len(s["roles"]) == 9 and all(
        len(r["ranks"]) == len(s["intensities"]) for r in s["roles"]
    )
    rows = what_if(pack, LEVELS, {"budget_management": 3, "fpa": 3}, "moderate", EVIDENCE, None)
    budget = next(r for r in rows if r["role_id"] == "budget_analyst")
    assert budget["fit_then"] > budget["fit_now"] and before == LEVELS


def test_exact_plan_is_never_worse_than_greedy_within_the_same_budget() -> None:
    pack = load_pack()
    for role_id in ("finance_systems_analyst", "budget_analyst", "cost_accountant"):
        match = score_role(pack, pack.destination_roles[role_id], LEVELS, "fast", EVIDENCE)
        result = compare_plans(pack, match, LEVELS, 1, "fast", EVIDENCE)
        plans = result["plans"]
        assert result["exact"] and result["budget_hours"] == 12
        assert all(p["hours"] <= 12 for p in plans.values())
        assert (plans["best"]["essentials_reached"], plans["best"]["fit_after"]["fast"]) >= (
            plans["greedy"]["essentials_reached"],
            plans["greedy"]["fit_after"]["fast"],
        )
        robust = plans["robust"]["fit_after"]
        assert min(robust.values()) >= min(plans["greedy"]["fit_after"].values())


def test_decision_routes(client: TestClient) -> None:
    pid = create(client)
    assert client.get(f"/api/profiles/{pid}/questions").status_code == 200
    assert client.get(f"/api/profiles/{pid}/sensitivity").json()["roles"]
    what = client.post(f"/api/profiles/{pid}/whatif", json={"changes": {"sql": 3}}).json()
    assert what["roles"] and what["pathway"] is None  # no destination chosen yet
    assert (
        client.post(f"/api/profiles/{pid}/whatif", json={"changes": {"nope": 3}}).status_code == 422
    )
    assert (
        client.post(f"/api/profiles/{pid}/answer", json={"skill": "sql", "level": 3}).status_code
        == 200
    )
    assert client.get(f"/api/profiles/{pid}").json()["profile"]["skills"]["sql"]["level"] == 3
    assert client.get(f"/api/profiles/{pid}/plans?role_id=budget_analyst").json()["plans"]["greedy"]
    card = client.get(f"/api/profiles/{pid}/matches").json()["roles"][0]
    assert {"meters", "fit_range"} <= set(card)
    assert client.get("/api/pipeline/forecast-check").status_code == 200
