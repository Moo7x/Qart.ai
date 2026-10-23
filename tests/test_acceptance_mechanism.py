"""Acceptance check 10 (docs/PLAN.md §8): the central mechanism, end to end, scripted.

A published finding (source and date) → a task-change interpretation (observed, task-level) → a
scenario emphasis change (assumption) → a different score for profile A → a revision proposal
A must accept; the SAME finding gives profile B no change in its chosen role, and the reason is
visible (that role's skills link to no task the finding concerns). Collectors are fakes; the
pipeline, store, engine and API are the real ones.
"""

from typing import Any, cast

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from src.collectors.base import Collect, CollectorResult, SourceState
from src.evidence.store import Observation, query_observations
from src.pack import load_pack
from src.pipeline import run as pipeline

TASK = "16139"  # BI analysts: "Maintain or update business intelligence tools ... dashboards ..."
SERIES = "aei_task_collaboration_bucket_automation_pct"
RELEASE = "2026-06-26"


def finding(period: str, value: float) -> Observation:
    return Observation(
        source_id="anthropic_economic_index",
        series=SERIES,
        entity=f"{TASK} Maintain or update business intelligence tools.",
        geography="GLOBAL",
        period=period,
        value=value,
        unit="% of this task's conversations",
        url="https://huggingface.co/datasets/Anthropic/EconomicIndex",
        cited_span=f"{period} · GLOBAL · onet task · automation = {value}",
        method_version="aei/monthly-2026",
        published=RELEASE,
    )


def collectors(observations: list[Observation]) -> dict[str, Collect]:
    def aei(client: httpx.Client, state: SourceState) -> CollectorResult:
        return CollectorResult(observations, note="fake release")

    def empty(client: httpx.Client, state: SourceState) -> CollectorResult:
        return CollectorResult([], note="fake: nothing new")

    return {name: (aei if name == "aei" else empty) for name in pipeline.COLLECTORS}


def offline() -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(404)))


def profile(client: TestClient, destination: str, skills: dict[str, int]) -> str:
    body = {
        "situation": "working",
        "current_role": "cash_application_analyst",
        "weekly_hours": 6,
        "skills": {s: {"level": lvl, "source": "self"} for s, lvl in skills.items()},
    }
    pid: str = client.post("/api/profiles", json=body).json()["id"]
    client.post(f"/api/profiles/{pid}/destination", json={"role_id": destination})
    return pid


def fast_proposal(client: TestClient, pid: str) -> dict[str, Any]:
    proposals = client.get(f"/api/profiles/{pid}/changes").json()["proposals"]
    return next(p for p in proposals if p["scenario"] == "fast")


def role_delta(report: dict[str, Any], role_id: str) -> dict[str, Any]:
    return next(r for r in report["roles"] if r["role_id"] == role_id)


def test_one_finding_changes_profile_a_and_explains_why_profile_b_is_unchanged(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    engine: Engine = cast(FastAPI, client.app).state.engine

    def run() -> pipeline.RunSummary:
        return pipeline.run_pipeline(engine, "schedule", offline, retry_pause=0)

    monkeypatch.setattr(pipeline, "COLLECTORS", collectors([finding("2026-04", 40.0)]))
    assert run().status == "changed"
    a = profile(client, "o2c_reporting_analyst", {"dashboards": 1, "reporting": 2})
    b = profile(client, "budget_analyst", {"budget_management": 2, "fpa": 2})

    # 1. A new finding is published by a scheduled run, stored with its source and date.
    monkeypatch.setattr(pipeline, "COLLECTORS", collectors([finding("2026-05", 90.0)]))
    assert run().status == "changed"
    stored = [r for r in query_observations(engine) if r["series"] == SERIES]
    latest = max(stored, key=lambda r: r["period"])
    assert (latest["period"], latest["value"], latest["published"]) == ("2026-05", 90.0, RELEASE)

    # 2–4. A: the task-level observation moves the dashboards weight (scenario rule) and the score.
    report_a = fast_proposal(client, a)["report"]
    o2c = role_delta(report_a, "o2c_reporting_analyst")
    dashboards = next(w for w in o2c["weights"] if w["skill"] == "dashboards")
    assert (dashboards["share_before"], dashboards["share_after"]) == (40.0, 90.0)
    assert dashboards["basis_after"] == "task"  # observed on the linked O*NET task
    assert dashboards["after"] > dashboards["before"]  # complementing skill: more emphasis
    assert "(observed)" in dashboards["reason"] and "assumes" in dashboards["reason"]
    assert o2c["fit_after"] != o2c["fit_before"]
    assert any(e["after"] == 90.0 and e["published"] == RELEASE for e in report_a["evidence"])

    # 5. It is a proposal: A's accepted journey is unchanged until A accepts it.
    proposal = fast_proposal(client, a)
    assert proposal["actionable"] and report_a["recommendation_changed"]
    assert report_a["pathway"]["role_id"] == "o2c_reporting_analyst"
    before = client.get(f"/api/profiles/{a}/matches?scenario=fast").json()
    fit_now = next(r["fit"] for r in before["roles"] if r["role_id"] == "o2c_reporting_analyst")
    assert fit_now == o2c["fit_before"]
    url = f"/api/profiles/{a}/changes/{proposal['id']}"
    assert client.post(url, json={"decision": "accept"}).status_code == 200
    after = client.get(f"/api/profiles/{a}/matches?scenario=fast").json()
    fit_new = next(r["fit"] for r in after["roles"] if r["role_id"] == "o2c_reporting_analyst")
    assert fit_new == o2c["fit_after"]

    # 6. B: the same finding leaves B's chosen role unchanged, and the reason is visible.
    report_b = fast_proposal(client, b)["report"]
    budget = role_delta(report_b, "budget_analyst")
    assert budget["weights"] == [] and budget["fit_after"] == budget["fit_before"]
    assert report_b["pathway"]["before"] == report_b["pathway"]["after"]
    pack = load_pack()
    role = pack.destination_roles["budget_analyst"]
    linked = {str(t.task) for r in role.requires for t in pack.tasks_for(role.soc, r.skill)}
    assert TASK not in linked  # why: no budget-analyst skill links to the task the finding is about
    tasks_b = client.get(f"/api/profiles/{b}/roles/budget_analyst/tasks").json()
    assert TASK not in {t["task"] for t in tasks_b["tasks"]}
