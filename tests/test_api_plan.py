"""GET /api/learning-plan/{user_id}: the plan with role, swaps, SDG targets and funding links."""

from fastapi.testclient import TestClient

LEVELS = {
    "spreadsheet_modelling": "sometimes",
    "financial_reporting": "sometimes",
    "recon_to_source": "confident",
}


def set_answers(client: TestClient, **prefs: object) -> None:
    profile = client.get("/api/profile/u_aina").json()
    merged = {**profile.get("preferences", {}), "current_job": "reconciliation_associate", **prefs}
    assert client.post("/api/profile", json={**profile, "preferences": merged}).status_code == 200


def test_plan_for_the_top_role_with_links_and_catalogue_state(client: TestClient) -> None:
    set_answers(client, skill_levels=LEVELS, direction="adjacent", timeframe_months=6)
    body = client.get("/api/learning-plan/u_aina").json()
    assert (
        not body["empty_profile"] and body["role"]["role_id"] == body["other_roles"][0]["role_id"]
    )
    plan = body["plan"]
    assert plan["steps"] and plan["summary"]["timeframe_weeks"] == 26
    assert all({"start_week", "end_week", "hours", "sdg_targets"} <= set(s) for s in plan["steps"])
    assert {link["url"][:8] for link in body["funding_links"]} == {"https://"}
    assert body["catalogue"]["verified"] >= 26 and body["catalogue"]["drafts_in_use"] is False
    assert all(body["alternatives"][a]["title"] for s in plan["steps"] for a in s["alternatives"])


def test_choosing_a_role_and_swapping_a_course(client: TestClient) -> None:
    set_answers(client, skill_levels=LEVELS, direction="adjacent")
    roles = client.get("/api/learning-plan/u_aina").json()["other_roles"]
    second = roles[1]["role_id"]
    assert (
        client.get(f"/api/learning-plan/u_aina?role_id={second}").json()["role"]["role_id"]
        == second
    )
    base = client.get("/api/learning-plan/u_aina").json()["plan"]["steps"]
    step = next((s for s in base if s["kind"] == "course" and s["alternatives"]), None)
    if step:
        swap = f"{step['skill_ids'][0]}:{step['alternatives'][0]}"
        swapped = client.get(f"/api/learning-plan/u_aina?swap={swap}").json()
        assert any(s["resource_id"] == step["alternatives"][0] for s in swapped["plan"]["steps"])
    assert client.get("/api/learning-plan/u_aina?swap=bad").status_code == 422
    assert client.get("/api/learning-plan/u_aina?role_id=astronaut").status_code == 404


def test_sparse_profile_has_no_plan(client: TestClient) -> None:
    set_answers(client, skill_levels={"customer_service": "sometimes"})
    body = client.get("/api/learning-plan/u_aina").json()
    assert body["empty_profile"] and body["plan"] is None and body["message"]
