"""The journey API: intake → profile → ranked roles → destination → pathway → future you."""

from typing import Any

from fastapi.testclient import TestClient

NUR = {
    "situation": "working",
    "current_role": "cash_application_analyst",
    "years_experience": 6,
    "weekly_hours": 6,
    "interests": ["data_digital"],
    "skills": {
        "cash_application": {
            "level": 3,
            "evidence": "Applied incoming customer receipts",
            "source": "cv",
        },
        "reconciliation": {
            "level": 3,
            "evidence": "Reconciled daily bank statements",
            "source": "cv",
        },
        "credit_collections": {"level": 2, "source": "self"},
        "reporting": {"level": 2, "source": "self"},
        "sql": {"level": None, "source": "self"},
    },
}


def create(client: TestClient, body: dict[str, Any] = NUR) -> str:
    response = client.post("/api/profiles", json=body)
    assert response.status_code == 201, response.text
    profile_id: str = response.json()["id"]
    return profile_id


def test_pack_lists_skills_roles_and_synthetic_samples(client: TestClient) -> None:
    body = client.get("/api/pack").json()
    assert len(body["destination_roles"]) == 9
    assert {s["id"] for s in body["samples"]} == {"nur", "hafiz", "mei"}
    assert "THIS PERSON DOES NOT EXIST" in client.get("/api/samples/nur").json()["text"]


def test_parse_scrubs_and_labels_the_fallback(client: TestClient) -> None:
    text = client.get("/api/samples/nur").json()["text"]
    body = client.post("/api/intake/parse", json={"text": text}).json()
    assert body["engine"] == "BM25 keywords (fallback)"  # tests never call the paid model
    assert body["removed"]["name"] == 1
    assert "nur.aisyah" not in str(body)


def test_upload_reads_text_files_and_refuses_others(client: TestClient) -> None:
    ok = client.post(
        "/api/intake/upload",
        files={
            "file": (
                "cv.txt",
                b"Cash Application Analyst. Reconciled bank statements daily.",
                "text/plain",
            )
        },
    )
    assert ok.status_code == 200
    bad = client.post("/api/intake/upload", files={"file": ("cv.exe", b"MZ", "application/x")})
    assert bad.status_code == 415


def test_matches_rank_every_role_with_reasons_and_sources(client: TestClient) -> None:
    profile_id = create(client)
    body = client.get(f"/api/profiles/{profile_id}/matches").json()
    assert body["scenario"] == "moderate"
    assert len(body["roles"]) == 9
    first = body["roles"][0]
    assert first["requirements"] and first["outlook"] and first["sdgs"]
    assert all(o["source"] for o in first["outlook"])
    assert body["current_role"]["id"] == "cash_application_analyst"


def test_fast_scenario_changes_requirements_but_never_the_persons_skills(
    client: TestClient,
) -> None:
    profile_id = create(client)
    moderate = client.get(f"/api/profiles/{profile_id}/matches?scenario=moderate").json()
    fast = client.get(f"/api/profiles/{profile_id}/matches?scenario=fast").json()
    assert fast["scenario_label"] == "Fast AI adoption"
    claimed = {r["skill"]: r["claimed"] for r in moderate["roles"][0]["requirements"]}
    fast_role = next(r for r in fast["roles"] if r["role_id"] == moderate["roles"][0]["role_id"])
    assert claimed == {r["skill"]: r["claimed"] for r in fast_role["requirements"]}
    stored = client.get(f"/api/profiles/{profile_id}").json()["profile"]["skills"]
    assert stored["reconciliation"]["level"] == 3


def test_destination_persists_and_drives_the_pathway(client: TestClient) -> None:
    profile_id = create(client)
    assert client.get(f"/api/profiles/{profile_id}/pathway").status_code == 409
    chosen = client.post(
        f"/api/profiles/{profile_id}/destination", json={"role_id": "o2c_reporting_analyst"}
    )
    assert chosen.status_code == 200
    assert (
        client.get(f"/api/profiles/{profile_id}").json()["destination"] == "o2c_reporting_analyst"
    )
    path = client.get(f"/api/profiles/{profile_id}/pathway").json()
    assert path["role_id"] == "o2c_reporting_analyst"
    assert path["steps"] and all(s["sdgs"] for s in path["steps"])
    assert path["courses_checked"]


def test_future_compares_today_and_after_in_both_scenarios(client: TestClient) -> None:
    profile_id = create(client)
    client.post(f"/api/profiles/{profile_id}/destination", json={"role_id": "cost_accountant"})
    body = client.get(f"/api/profiles/{profile_id}/future").json()
    for scenario in ("moderate", "fast"):
        view = body["scenarios"][scenario]
        assert view["fit_after"] >= view["fit_now"]
        assert all(s["after"] >= (s["now"] or 0) for s in view["skills"])


def test_unknown_profile_is_404_and_bad_input_is_422(client: TestClient) -> None:
    assert client.get("/api/profiles/does-not-exist/matches").status_code == 404
    bad = {**NUR, "skills": {"time_travel": {"level": 2}}}
    assert client.post("/api/profiles", json=bad).status_code == 422
    assert client.post("/api/profiles", json={**NUR, "weekly_hours": 0}).status_code == 422
