"""The CV draft uses only confirmed data, keeps learning apart from experience and shows a diff."""

from fastapi.testclient import TestClient

from src.cv.draft import build_draft
from src.journey.store import ProfileData, SkillClaim
from src.pack import load_pack
from tests.test_api_journey import create


def test_draft_uses_only_what_the_person_confirmed() -> None:
    pack = load_pack()
    course = next(iter(pack.courses))
    profile = ProfileData(
        situation="working",
        current_role="cash_application_analyst",
        skills={
            "reconciliation": SkillClaim(
                level=3, evidence="Reconciled daily bank statements.", source="cv"
            ),
            "sql": SkillClaim(level=None, source="self"),  # not stated: not on the CV
        },
    )
    draft = build_draft(pack, profile, "o2c_reporting_analyst", None, [course, "not-a-course"])
    assert draft["headline"] == [
        "Cash Application Analyst, building towards Order-to-Cash (O2C) Reporting Analyst."
    ]
    assert draft["skills"] == ["Reconciliation Processes — own rating: 4 of 5 (proficient)"]
    assert draft["experience"] == ["Reconciled daily bank statements."]
    assert len(draft["learning"]) == 1 and "completed, self-reported" in draft["learning"][0]


def test_accepting_makes_a_version_and_the_next_draft_shows_its_diff(client: TestClient) -> None:
    pid = create(client)
    first = client.get(f"/api/profiles/{pid}/cv").json()
    assert first["versions"] == [] and first["diff"]["skills"]["added"]
    assert client.post(f"/api/profiles/{pid}/cv/accept").json() == {"version": 1}
    assert client.get(f"/api/profiles/{pid}/cv").json()["unchanged"] is True
    client.post(f"/api/profiles/{pid}/answer", json={"skill": "sql", "level": 2})
    later = client.get(f"/api/profiles/{pid}/cv").json()
    assert later["diff"]["skills"]["added"] and later["unchanged"] is False


def test_accepting_only_the_ticked_changes(client: TestClient) -> None:
    pid = create(client)
    first = client.get(f"/api/profiles/{pid}/cv").json()
    skipped = first["diff"]["skills"]["added"][0]
    body = {"skip_added": [skipped, "Invented line that was never suggested"]}
    assert client.post(f"/api/profiles/{pid}/cv/accept", json=body).json() == {"version": 1}
    after = client.get(f"/api/profiles/{pid}/cv").json()
    assert skipped not in after["current"]["skills"]
    assert "Invented line that was never suggested" not in str(after["current"])
    assert after["diff"]["skills"]["added"] == [skipped]  # still offered next time
