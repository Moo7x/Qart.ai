"""Badges (C5) come only from events and reward only what happened."""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient

from src.journey.events import badges
from src.match.engine import Evidence, score_role
from src.pack import load_pack
from src.pathway.planner import plan_pathway

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")
ROLE = "cost_accountant"


def _plan():  # type: ignore[no-untyped-def]
    pack = load_pack()
    match = score_role(pack, pack.destination_roles[ROLE], {}, "moderate", EVIDENCE)
    return plan_pathway(pack, match, {}, 6, "moderate", EVIDENCE)


def _event(i: int, kind: str, ref: str, before: Any = None, after: Any = None) -> dict[str, Any]:
    return {
        "id": i,
        "at": datetime(2026, 10, 30, tzinfo=UTC) + timedelta(minutes=i),
        "kind": kind,
        "ref": ref,
        "before": before,
        "after": after,
    }


def _ids(found: list[dict[str, Any]]) -> list[str]:
    return [b["id"] for b in found]


def test_no_event_no_badge() -> None:
    assert badges(load_pack(), [], ROLE, _plan()) == []


def test_undoing_a_course_removes_halfway_but_first_step_stays() -> None:
    plan = _plan()
    courses = [s.course.id for s in plan.steps]
    done = [_event(i, "course_done", c) for i, c in enumerate(courses)]
    found = badges(load_pack(), done, ROLE, plan)
    assert "first_step" in _ids(found) and "halfway" in _ids(found)
    undone = [_event(len(done) + i, "course_undone", c) for i, c in enumerate(courses)]
    after = badges(load_pack(), done + undone, ROLE, plan)
    assert "first_step" in _ids(after) and "halfway" not in _ids(after)
    first = next(b for b in after if b["id"] == "first_step")
    assert first["evidence"] == {"kind": "course_done", "ref": courses[0]}


def test_an_accepted_check_that_raises_a_required_skill_earns_skill_up() -> None:
    skill = load_pack().destination_roles[ROLE].requires[0].skill
    events = [
        _event(1, "level_changed", skill, None, {"level": 2, "source": "cv"}),  # initial: nothing
        _event(2, "level_changed", skill, 2, {"level": 3, "source": "agent_check"}),
    ]
    found = badges(load_pack(), events[:1], ROLE, _plan())
    assert not any(b["id"].startswith("skill_up") for b in found)
    found = badges(load_pack(), events, ROLE, _plan())
    ups = [b for b in found if b["id"].startswith("skill_up")]
    assert len(ups) == 1 and ups[0]["evidence"] == {"kind": "level_changed", "ref": skill}


def test_a_rise_on_a_skill_the_destination_does_not_need_earns_nothing() -> None:
    needed = {r.skill for r in load_pack().destination_roles[ROLE].requires}
    other = next(s for s in load_pack().skills if s not in needed)
    events = [_event(1, "level_changed", other, 1, {"level": 2, "source": "self"})]
    assert badges(load_pack(), events, ROLE, _plan()) == []


def test_plan_complete_needs_every_step_and_never_counts_a_skip() -> None:
    plan = _plan()
    done = [_event(i, "course_done", s.course.id) for i, s in enumerate(plan.steps)]
    skipped = [_event(50 + i, "step_skipped", p.id) for i, p in enumerate(plan.practice_steps)]
    assert "plan_complete" not in _ids(badges(load_pack(), done + skipped, ROLE, plan))
    reached = [
        _event(80 + i, "level_changed", p.skill, 2, {"level": p.target_level, "source": "self"})
        for i, p in enumerate(plan.practice_steps)
    ]
    assert "plan_complete" in _ids(badges(load_pack(), done + reached, ROLE, plan))


def test_badges_api_returns_c5_shape(client: TestClient) -> None:
    pid = client.post("/api/profiles", json={"situation": "working"}).json()["id"]
    assert client.get(f"/api/profiles/{pid}/badges").json() == []
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": ROLE})
    course = client.get(f"/api/profiles/{pid}/pathway").json()["steps"][0]["course"]["id"]
    client.put(f"/api/profiles/{pid}/progress", json={"done": [course]})
    found = client.get(f"/api/profiles/{pid}/badges").json()
    assert found[0]["id"] == "first_step"
    assert set(found[0]) == {"id", "title", "earned_at", "rule", "evidence"}
    assert found[0]["evidence"] == {"kind": "course_done", "ref": course}
