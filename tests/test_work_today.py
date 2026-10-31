"""Your work today: the current job's tasks with the four kinds of evidence, kept apart."""

from fastapi.testclient import TestClient

NUR = {
    "situation": "working",
    "current_role": "cash_application_analyst",
    "skills": {
        "reconciliation": {"level": 3, "evidence": "Reconciled bank statements", "source": "cv"}
    },
}


def test_work_today_names_the_job_and_keeps_missing_evidence_missing(client: TestClient) -> None:
    pid = client.post("/api/profiles", json=NUR).json()["id"]
    body = client.get(f"/api/profiles/{pid}/work-today").json()
    assert body["role"]["id"] == "cash_application_analyst"
    assert body["role"]["source"].startswith("TalentCorp (2024) GBS study, PDF p.")
    assert body["deployment"] is None  # not collected: never shown as zero
    assert body["task_source"] in ("onet", "ilo")
    for task in body["tasks"]:
        assert task["observed_use"] is None or task["observed_use"]["period"]
        assert not task["you_do_this"] or task["quote"]


def test_work_today_needs_a_current_job(client: TestClient) -> None:
    body = {"situation": "student", "skills": {}}
    pid = client.post("/api/profiles", json=body).json()["id"]
    assert client.get(f"/api/profiles/{pid}/work-today").status_code == 409


def test_linked_tasks_mark_what_the_cv_shows(client: TestClient) -> None:
    body = {
        "situation": "working",
        "current_role": "master_data_management_analyst",
        "skills": {
            "data_management": {
                "level": 3,
                "evidence": "Owned the vendor master data",
                "source": "cv",
            }
        },
    }
    pid = client.post("/api/profiles", json=body).json()["id"]
    out = client.get(f"/api/profiles/{pid}/work-today").json()
    assert out["task_source"] == "onet" and out["tasks"]
    first = out["tasks"][0]
    assert first["you_do_this"] and first["skill"] == "data_management"
    assert first["quote"] == "Owned the vendor master data"


def test_market_items_carry_source_period_and_direction() -> None:
    from src.evidence.signals import Point, Signal
    from src.match.outlook import occupation_market

    signal = Signal(
        id="dosm_share_clerical",
        title="Clerical support workers: share of employees",
        family="share",
        kind="observed",
        direction="weakening",
        early_direction="down",
        headline="13.1% in 2025",
        unit="% of employees",
        points=[Point(period="2024", value=13.4), Point(period="2025", value=13.1)],
        independent_sources=1,
        note="",
        sources=[],
        evidence=[],
    )
    [item] = occupation_market("43-3031.00", [signal])
    assert item["kind"] == "observed" and item["period"] == "2025"
    assert item["direction"] == "weakening" and item["source"].startswith("DOSM")
    assert occupation_market("43-3031.00", []) == []
