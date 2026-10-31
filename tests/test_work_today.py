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
