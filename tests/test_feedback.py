"""Feedback: preferences stay personal, errors are reviewed, corrections are tested then applied."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from src.pack import load_pack, set_unavailable, unavailable
from tests.test_api_journey import create

ADMIN = {"x-admin-token": "test-admin-token"}


@pytest.fixture(autouse=True)
def clean_corrections() -> Iterator[None]:
    yield
    set_unavailable(set())  # the registry is process-wide; never leak into other tests


def report(client: TestClient, **body: str) -> dict[str, object]:
    response = client.post("/api/feedback", json={"page": "test", **body})
    assert response.status_code == 201, response.text
    data: dict[str, object] = response.json()
    return data


def test_preference_is_personal_and_never_enters_review(client: TestClient) -> None:
    pid = create(client)
    out = report(
        client, kind="not_my_goal", target_type="role", target_id="budget_analyst", profile_id=pid
    )
    assert out["route"] == "preference"
    assert client.get(f"/api/profiles/{pid}/preferences").json()["not_my_goal"] == [
        "budget_analyst"
    ]
    assert client.get("/api/feedback", headers=ADMIN).json()["queue"] == []


def test_course_report_is_evaluated_then_released_for_everyone(client: TestClient) -> None:
    course = next(iter(load_pack().courses))
    out = report(client, kind="course_unavailable", target_type="course", target_id=course)
    assert out["route"] == "error" and out["proposal"] == {
        "action": "mark_course_unavailable",
        "course_id": course,
    }
    fid = out["id"]
    assert client.get("/api/feedback").status_code == 403  # admin only
    check = client.get(f"/api/feedback/{fid}/evaluate", headers=ADMIN).json()["evaluation"]
    assert check["plans"] > 0 and check["plans_changed"] >= 0
    assert course not in unavailable()  # evaluating changes nothing
    done = client.post(
        f"/api/feedback/{fid}/decide", json={"decision": "accept"}, headers=ADMIN
    ).json()
    assert done["decision"] == "released" and course in unavailable()
    assert all(c.id != course for s in load_pack().skills for c in load_pack().courses_for(s))
    again = client.post(f"/api/feedback/{fid}/decide", json={"decision": "accept"}, headers=ADMIN)
    assert again.status_code == 409
    assert (
        client.get("/api/feedback", headers=ADMIN).json()["releases"][0]["action"]
        == "mark_course_unavailable"
    )


def test_rejected_report_changes_nothing(client: TestClient) -> None:
    out = report(
        client, kind="unsupported_claim", target_type="evidence", target_id="x", message="wrong"
    )
    done = client.post(
        f"/api/feedback/{out['id']}/decide", json={"decision": "reject"}, headers=ADMIN
    ).json()
    assert done["decision"] == "rejected" and unavailable() == frozenset()
