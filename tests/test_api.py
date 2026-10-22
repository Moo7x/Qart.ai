"""Engine API (Task A6): contract shapes, validation, privacy, and the golden journey over HTTP."""

from typing import Any

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.contract import (
    CompanyAssumptions,
    NextCase,
    PathPlan,
    Recommendation,
    Role,
    SkillState,
    Snapshot,
    SnapshotDiff,
)
from tests.helpers import golden_journey_raw

SKILL = "unsupported_adjustment"


def skill(states: list[dict[str, Any]], skill_id: str = SKILL) -> SkillState:
    return SkillState.model_validate(next(s for s in states if s["skill_id"] == skill_id))


def post_golden_events(client: TestClient) -> list[dict[str, Any]]:
    states: list[dict[str, Any]] = []
    for event in golden_journey_raw()["events"]:
        response = client.post("/api/events", json=event)
        assert response.status_code == 200, response.text
        states = response.json()
    return states


# --- basic endpoints ------------------------------------------------------------------------
def test_aina_profile_loads_with_self_rating(client: TestClient) -> None:
    states = client.get("/api/skills/u_aina").json()
    state = skill(states)
    assert state.state == "self_reported" and "8/10" in state.why
    assert len(states) == 16


def test_unknown_user_is_404(client: TestClient) -> None:
    assert client.get("/api/skills/u_nobody").status_code == 404
    assert client.get("/api/recommendations/u_nobody").status_code == 404


def test_post_profile_returns_profile_and_initial_states(client: TestClient) -> None:
    body = {
        "id": "u_new",
        "display_name": "New (synthetic)",
        "current_role_id": "recon_associate",
        "years_experience": 1,
        "skills_self_reported": [{"skill_id": "fx_conversion", "confidence": 0.6}],
        "interests": ["analysis"],
        "weekly_learning_hours": 3,
        "language": "en",
        "team": "finops_kl",
    }
    response = client.post("/api/profile", json=body)
    assert response.status_code == 200
    assert response.json()["profile"]["id"] == "u_new"
    assert skill(response.json()["skills"], "fx_conversion").state == "self_reported"
    bad = {**body, "skills_self_reported": [{"skill_id": "juggling", "confidence": 0.5}]}
    assert client.post("/api/profile", json=bad).status_code == 422


def test_roles_snapshots_assumptions_shapes(client: TestClient) -> None:
    roles = [Role.model_validate(r) for r in client.get("/api/roles").json()]
    assert {r.id for r in roles} >= {"recon_associate", "ai_finops_analyst"}
    snaps = [Snapshot.model_validate(s) for s in client.get("/api/snapshots").json()]
    assert [s.id for s in snaps] == ["snap_aei_2026_04"]
    assumptions = CompanyAssumptions.model_validate(client.get("/api/assumptions").json())
    assert assumptions.version == 1


def test_event_validation(client: TestClient) -> None:
    event = golden_journey_raw()["events"][0]
    assert client.post("/api/events", json=event).status_code == 200
    assert client.post("/api/events", json=event).status_code == 409
    checkin = {**golden_journey_raw()["events"][2], "id": "ev_x", "help_level_max": 1}
    assert client.post("/api/events", json=checkin).status_code == 422
    unknown = {
        **event,
        "id": "ev_y",
        "skills_evidence": [{"skill_id": "juggling", "outcome": "success", "help_level": 0}],
    }
    assert client.post("/api/events", json=unknown).status_code == 422


def test_flagged_event_stops_counting(client: TestClient) -> None:
    post_golden_events(client)
    response = client.post(
        "/api/events/ev_0002/flag", json={"flag": "companion_error", "set_by": "senior"}
    )
    assert response.status_code == 200
    state = skill(response.json()["skills"])
    assert state.counted_events == 2
    assert any(not t.counted for t in state.evidence_trail)
    recommendation = client.get("/api/recommendations/u_aina").json()
    assert recommendation["changed_since"] is not None


# --- golden journey steps 2-5 ---------------------------------------------------------------
def test_golden_journey_changes_skills_next_case_and_path(client: TestClient) -> None:
    path_before = PathPlan.model_validate(
        client.get("/api/path/u_aina?role_id=ai_finops_analyst").json()
    )
    events = golden_journey_raw()["events"]

    client.post("/api/events", json=events[0])
    nxt = NextCase.model_validate(client.get("/api/next-case/u_aina").json())
    assert nxt.case_id == "case_006" and "case_003" in nxt.because

    client.post("/api/events", json=events[1])
    nxt = NextCase.model_validate(client.get("/api/next-case/u_aina").json())
    assert nxt.case_id == "checkin_001"

    states = client.post("/api/events", json=events[2]).json()
    state = skill(states)
    assert state.state == "observed_with_help"
    assert state.why.startswith("1 of 2 independent successes (checkin_001).")
    assert state.next_to_confirm == "checkin_002 (later session)"

    path_after = PathPlan.model_validate(
        client.get("/api/path/u_aina?role_id=ai_finops_analyst").json()
    )
    before = [(s.type, s.ref) for s in path_before.steps if SKILL in s.skills]
    after = [(s.type, s.ref) for s in path_after.steps if SKILL in s.skills]
    assert before and all(kind != "checkin" for kind, _ in before)
    assert after == [("checkin", "checkin_002")]

    rec = Recommendation.model_validate(client.get("/api/recommendations/u_aina").json())
    assert rec.changed_since is not None and rec.changed_since.rank_changes
    assert all("checkin_001" in c.because for c in rec.changed_since.rank_changes)


def test_smaller_weekly_hours_changes_the_api_plan(client: TestClient) -> None:
    wide = client.get("/api/path/u_aina?weekly_hours=4").json()
    narrow = client.get("/api/path/u_aina?weekly_hours=1").json()
    assert [s["ref"] for s in wide["steps"]] != [s["ref"] for s in narrow["steps"]]
    assert client.get("/api/path/u_aina?weekly_hours=0").status_code == 422


# --- golden journey step 6: evidence → review → approval → recompute ------------------------
def test_snapshot_ingest_review_approval_changes_card_and_ranking(client: TestClient) -> None:
    post_golden_events(client)
    before = Recommendation.model_validate(
        client.get("/api/recommendations/u_aina?scenario=assistive").json()
    )

    ingest = client.post("/api/ingest/run").json()
    assert ingest["ingested"] == "snap_aei_2026_05" and ingest["label"] == "historical data replay"
    diff = SnapshotDiff.model_validate(client.get("/api/snapshots/diff").json())
    review_ids = {r.assumption_id for r in diff.suggested_assumption_reviews}
    assert "assistive.check_entries" in review_ids
    assert client.post("/api/ingest/run").json()["ingested"] is None

    # Ingesting alone never changes weights (layer A is evidence only).
    same = Recommendation.model_validate(
        client.get("/api/recommendations/u_aina?scenario=assistive").json()
    )
    assert [(r.role_id, r.score) for r in same.roles] == [
        (r.role_id, r.score) for r in before.roles
    ]

    assumptions = client.get("/api/assumptions").json()
    assumptions["scenarios"]["assistive"]["tasks"]["check_entries"] = "ai_drafts_human_reviews"
    assumptions["based_on_snapshot"] = "snap_aei_2026_05"
    assumptions["change_note"] = "AI drafts entry checks (review of AEI May 2026)"
    approved = client.put("/api/assumptions", json=assumptions)
    assert approved.status_code == 200 and approved.json()["version"] == 2

    after = Recommendation.model_validate(
        client.get("/api/recommendations/u_aina?scenario=assistive").json()
    )
    assert after.assumptions_version == 2 and after.snapshot_id == "snap_aei_2026_05"

    def card(rec: Recommendation, role_id: str) -> Any:
        return next(r for r in rec.roles if r.role_id == role_id).requirement_card

    old_card, new_card = card(before, "recon_associate"), card(after, "recon_associate")
    task = next(t for t in new_card.tasks if t.workflow_task == "check_entries")
    assert task.allocation == "ai_drafts_human_reviews"
    assert new_card.weights != old_card.weights
    assert any("assumption v2" in w.because for w in new_card.weights)
    assert any("AEI 2026-05" in e.label for e in new_card.evidence)

    assert [(r.role_id, r.score) for r in after.roles] != [
        (r.role_id, r.score) for r in before.roles
    ]
    assert after.changed_since is not None and after.changed_since.assumptions_version == 1
    assert any("v1 → v2" in c.because for c in after.changed_since.rank_changes)
    outlook = {c.role_id: c for c in after.changed_since.outlook_changes}
    assert outlook["recon_associate"].from_label == "stable"
    assert outlook["recon_associate"].to_label == "being transformed"
    recon = next(r for r in after.roles if r.role_id == "recon_associate")
    assert recon.outlook is not None and recon.outlook == new_card.outlook


def test_put_assumptions_rejects_changed_task_list(client: TestClient) -> None:
    assumptions = client.get("/api/assumptions").json()
    assumptions["scenarios"]["assistive"]["tasks"]["new_task"] = "ai"
    assert client.put("/api/assumptions", json=assumptions).status_code == 422


# --- HR aggregates --------------------------------------------------------------------------
def test_hr_summary_is_aggregate_only_and_suppresses_small_groups(client: TestClient) -> None:
    summary = client.get("/api/hr/summary?team=finops_kl").json()
    assert summary["group_size"] == 9 and not summary["suppressed"]
    text = str(summary)
    for name in ("Aina", "Siti", "u_aina", "u_siti"):
        assert name not in text
    for row in summary["skills"]:
        values = list(row["counts"].values())
        assert all(v is None or v == 0 or v >= 5 for v in values)
        assert sum(v is None for v in values) != 1  # no single hidden cell to subtract
    assert {d["scenario"] for d in summary["training_demand"]} == {"assistive", "agentic"}
    small = client.get("/api/hr/summary?team=ap_penang").json()
    assert small["suppressed"] and small["skills"] == [] and small["group_size"] is None


# --- optimiser stub and demo reset ----------------------------------------------------------
def test_optimizer_proposals_start_empty_and_unknown_decision_is_404(client: TestClient) -> None:
    assert client.get("/api/optimizer/proposals").json() == []
    body = {"decision": "approve", "decided_by": "senior (synthetic)"}
    assert client.post("/api/optimizer/proposals/opt_x/decision", json=body).status_code == 404


def test_demo_reset_restores_the_seed(client: TestClient) -> None:
    post_golden_events(client)
    client.post("/api/ingest/run")
    reset = client.post("/api/demo/reset").json()
    assert reset == {
        "status": "reset",
        "people": 12,
        "active_snapshots": ["snap_aei_2026_04"],
        "assumptions_version": 1,
    }
    assert skill(client.get("/api/skills/u_aina").json()).state == "self_reported"


def test_recommendation_never_exposes_a_percentage_state(client: TestClient) -> None:
    post_golden_events(client)
    states = client.get("/api/skills/u_aina").json()
    for state in states:
        assert "%" not in state["why"]


def test_record_event_can_be_called_in_process(client: TestClient) -> None:
    """The companion records graded events without HTTP; validation is the same as the route."""
    from src.api_engine import get_store, record_event
    from src.contract import Event
    from src.main import app

    store = app.dependency_overrides[get_store]()
    event = Event.model_validate(golden_journey_raw()["events"][0])
    states = record_event(event, store)
    assert skill([s.model_dump() for s in states]).counted_events == 1
    with pytest.raises(HTTPException) as duplicate:
        record_event(event, store)
    assert duplicate.value.status_code == 409
