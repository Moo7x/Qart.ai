"""Unlocking (B4): course steps in order, practice after its study, completion from the claim."""

from fastapi.testclient import TestClient

from src.journey.store import SkillClaim
from src.match.engine import Evidence, score_role
from src.pack import load_pack
from src.pathway.planner import apply_progress, plan_pathway

EVIDENCE = Evidence(automation_share={}, automation_period="", automation_source="")
ROLE = "o2c_reporting_analyst"


def _path():  # type: ignore[no-untyped-def]
    pack = load_pack()
    match = score_role(pack, pack.destination_roles[ROLE], {}, "moderate", EVIDENCE)
    return plan_pathway(pack, match, {}, 6, "moderate", EVIDENCE)


def test_course_steps_unlock_in_order() -> None:
    path = apply_progress(_path(), [], [], {})
    assert not path.steps[0].locked and all(s.locked for s in path.steps[1:])
    first = path.steps[0].course.id
    path = apply_progress(_path(), [first], [], {})
    assert path.steps[0].done and not path.steps[1].locked


def test_practice_unlocks_when_its_study_is_done() -> None:
    path = _path()
    practice = path.practice_steps[0]
    study = [
        s.course.id
        for s in path.steps
        if s.skill == practice.skill or practice.skill in s.course.covers
    ]
    assert apply_progress(_path(), [], [], {}).practice_steps[0].locked == bool(study)
    unlocked = apply_progress(_path(), study, [], {}).practice_steps[0]
    assert not unlocked.locked and unlocked.status == "open"


def test_practice_completes_from_an_agent_check_or_a_self_rerate() -> None:
    practice = _path().practice_steps[0]
    checked = SkillClaim(
        level=practice.target_level,
        source="agent_check",
        evidence="quote",
        checked_at="2026-10-30T10:00:00Z",
        model="gpt-4.1-mini",
    )
    done = apply_progress(_path(), [], [], {practice.skill: checked}).practice_steps[0]
    assert (done.status, done.status_label) == ("done", "checked")
    rerated = SkillClaim(level=practice.target_level, source="self")
    done = apply_progress(_path(), [], [], {practice.skill: rerated}).practice_steps[0]
    assert (done.status, done.status_label) == ("done", "self-rated")
    below = SkillClaim(level=practice.target_level - 1, source="agent_check", evidence="quote")
    assert (
        apply_progress(_path(), [], [], {practice.skill: below}).practice_steps[0].status == "open"
    )


def test_continue_anyway_is_stored_labelled_and_unknown_ids_are_dropped(client: TestClient) -> None:
    pid = client.post("/api/profiles", json={"situation": "working"}).json()["id"]
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": ROLE})
    step = client.get(f"/api/profiles/{pid}/pathway").json()["practice_steps"][0]
    saved = client.put(
        f"/api/profiles/{pid}/progress",
        json={"done": [], "skipped": [step["id"], "practice:quantum_ledger:3", "practice:erp:9"]},
    ).json()
    assert saved["skipped"] == [step["id"]]
    again = client.get(f"/api/profiles/{pid}/pathway").json()["practice_steps"][0]
    assert (again["status"], again["status_label"]) == ("skipped", "continued anyway, not done")
    # Saving progress without `skipped` keeps what was passed.
    kept = client.put(f"/api/profiles/{pid}/progress", json={"done": []}).json()
    assert kept["skipped"] == [step["id"]]
