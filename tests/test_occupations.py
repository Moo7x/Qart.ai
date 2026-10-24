"""Occupation catalogue, RunPod jobs and detection, with fake RunPod and O*NET responses."""

import csv
import dataclasses
import io
import json
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pytest
from sqlalchemy import Engine

import src.occupations.catalogue  # noqa: F401  (registers the tables before init_db)
from src.config import Settings
from src.db import init_db, make_engine
from src.occupations import catalogue as cat
from src.occupations.detect import detect
from src.runpod_jobs import RunPodError, run_job

OCCUPATIONS = [
    (
        "43-3031.00",
        "Bookkeeping, Accounting, and Auditing Clerks",
        "Compute and record financial data.",
    ),
    ("15-1252.00", "Software Developers", "Design and build computer software."),
    ("29-1141.00", "Registered Nurses", "Assess patient health problems."),
]


def onet_zip() -> bytes:
    def table(header: list[str], rows: list[list[Any]]) -> str:
        out = io.StringIO()
        w = csv.writer(out)
        w.writerow(header)
        w.writerows(rows)
        return out.getvalue()

    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as z:
        z.writestr(
            "db/occupation_data.csv",
            table(["O*NET-SOC Code", "Title", "Description"], [list(o) for o in OCCUPATIONS]),
        )
        z.writestr(
            "db/sample_of_reported_titles.csv",
            table(
                ["O*NET-SOC Code", "Title", "Reported Job Title", "Shown in My Next Move"],
                [
                    ["43-3031.00", "x", "Accounts Clerk", "Y"],
                    ["15-1252.00", "x", "Programmer", "Y"],
                ],
            ),
        )
        z.writestr(
            "db/task_statements.csv",
            table(
                ["O*NET-SOC Code", "Title", "Task ID", "Task", "Task Type"],
                [["43-3031.00", "x", "1", "Post journal entries.", "Core"]],
            ),
        )
        z.writestr(
            "db/task_ratings.csv",
            table(
                ["O*NET-SOC Code", "Task ID", "Scale ID", "Data Value"],
                [["43-3031.00", "1", "IM", "4.1"]],
            ),
        )
    return data.getvalue()


ESCO_CSV = "\n".join(
    [
        "Mapping project name,x",
        "",
        "O*NET Id,O*NET Title,O*NET Description,ESCO or ISCO URI,ESCO or ISCO Title,"
        "ESCO or ISCO Description,Type of Match",
        "43-3031.00,x,x,http://esco/a,bookkeeper,x,broadMatch",
        "43-3031.00,x,x,http://esco/b,accounting clerk,x,exactMatch",
    ]
)


def vector(i: int) -> list[float]:
    return [1.0 if j == i else 0.0 for j in range(3)]


def fake_services(log: list[str], embed_index: dict[str, int] | None = None) -> httpx.MockTransport:
    """O*NET, ESCO and a RunPod endpoint that answers after one IN_PROGRESS poll."""

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url.endswith("database.html"):
            return httpx.Response(200, text="db_31_0_csv.zip")
        if url.endswith("db_31_0_csv.zip"):
            return httpx.Response(200, content=onet_zip())
        if "esco.ec.europa.eu" in url:
            return httpx.Response(200, content=ESCO_CSV.encode())
        if url.endswith("/run"):
            payload = json.loads(request.content)["input"]
            log.append(payload["task"])
            out: dict[str, Any]
            if payload["task"] == "embed":
                texts = payload["texts"]
                pick = embed_index or {}
                out = {"vectors": [vector(pick.get(t.split(".")[0], 2)) for t in texts]}
            else:
                out = {"scores": [float(len(p)) for p in payload["passages"]]}
            return httpx.Response(200, json={"id": "job1", "status": "IN_QUEUE", "_out": out})
        if "/status/" in url:
            return httpx.Response(
                200, json={"id": "job1", "status": "COMPLETED", "output": _last[0]}
            )
        return httpx.Response(404)

    return httpx.MockTransport(handler)


_last: list[Any] = [None]


class Capture(httpx.MockTransport):
    """Keep the output of the last submitted job so the status poll can return it."""

    def __init__(self, inner: httpx.MockTransport) -> None:
        self.inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        response = self.inner.handle_request(request)
        if str(request.url).endswith("/run"):
            _last[0] = json.loads(response.content)["_out"]
        return response


@pytest.fixture(autouse=True)
def no_poll_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.runpod_jobs.POLL_SECONDS", 0.0)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    engine = make_engine(f"sqlite:///{(tmp_path / 'o.sqlite').as_posix()}")
    init_db(engine)
    return engine


def runpod_settings(settings: Settings) -> Settings:
    return dataclasses.replace(settings, runpod_api_key="k", runpod_endpoint_id="e")


def test_catalogue_keeps_titles_tasks_and_the_best_esco_match(engine: Engine) -> None:
    with httpx.Client(transport=Capture(fake_services([]))) as client:
        note = cat.refresh_catalogue(engine, client)
        again = cat.refresh_catalogue(engine, client)
    rows = {r["soc"]: r for r in cat.catalogue(engine)}
    clerk = rows["43-3031.00"]
    assert "3 occupations" in note and "current" in again
    assert json.loads(clerk["reported_titles"]) == ["Accounts Clerk"]
    assert json.loads(clerk["tasks"])[0]["importance"] == 4.1
    assert (clerk["esco_title"], clerk["esco_match"]) == ("accounting clerk", "exactMatch")
    assert "Also called: Accounts Clerk" in cat.search_text(clerk)


def test_index_is_built_once_and_detection_reranks(engine: Engine, settings: Settings) -> None:
    log: list[str] = []
    live = runpod_settings(settings)
    index = {"Bookkeeping, Accounting, and Auditing Clerks": 0, "Software Developers": 1}
    with httpx.Client(transport=Capture(fake_services(log, index))) as client:
        cat.refresh_catalogue(engine, client)
        assert "embedded 3" in cat.build_index(engine, live, client)
        assert "current" in cat.build_index(engine, live, client)
        found = detect(engine, live, "Bookkeeping, Accounting, and Auditing Clerks", client)
    assert log.count("embed") == 2 and log.count("rerank") == 1  # index once, then one query
    assert "RunPod" in found.engine and found.matches
    assert found.matches[0].in_field is (found.matches[0].soc == "43-3031.00")


def test_detection_falls_back_to_keywords_and_says_so(engine: Engine, settings: Settings) -> None:
    with httpx.Client(transport=Capture(fake_services([]))) as client:
        cat.refresh_catalogue(engine, client)
    found = detect(engine, settings, "accounts clerk")
    assert found.engine == "BM25 keywords (fallback)" and "not configured" in found.note
    assert found.matches[0].soc == "43-3031.00" and found.matches[0].in_field


def test_run_job_gives_up_at_the_budget(settings: Settings) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"id": "j", "status": "IN_QUEUE"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client, pytest.raises(RunPodError):
        run_job(
            runpod_settings(settings),
            {"task": "embed", "texts": ["x"]},
            -1.0,
            client,
            sleep=lambda s: None,
        )


def test_preview_uses_the_field_link_and_labels_coverage(engine: Engine) -> None:
    from src.occupations.preview import preview

    with httpx.Client(transport=Capture(fake_services([]))) as client:
        cat.refresh_catalogue(engine, client)
        rows: list[dict[str, Any]] = [
            {
                "source_id": "anthropic_economic_index",
                "series": "aei_pct",
                "entity": "43-3031.00 x",
                "geography": "GLOBAL",
                "period": "2026-05",
                "value": 0.3,
                "url": "u",
                "cited_span": "",
            },
        ]
        clerk = preview(engine, "43-3031.00", rows, [], client)
        nurse = preview(engine, "29-1141.00", [], [], client)
        assert preview(engine, "00-0000.00", [], [], client) is None
    assert clerk is not None and nurse is not None
    assert clerk["in_field"] and clerk["isco"] == "4311"  # verified field link, no ESCO call
    assert clerk["ai_use"]["share"] == 0.3 and clerk["ai_use"]["share_local"] is None
    assert not nurse["in_field"] and nurse["isco"] is None and nurse["isco_note"]  # said why
    assert "Evidence preview only" in nurse["coverage"]


def test_detect_route_returns_labelled_suggestions(client: Any) -> None:
    status = client.get("/api/occupations/status").json()
    assert status["occupations"] == 0 and status["vectors"] == 0
    assert "Kerani akaun" in status["examples"]
    body = client.post("/api/occupations/detect", json={"text": "accounts clerk"}).json()
    assert body["engine"] == "none" and body["matches"] == []  # empty catalogue in tests
    assert client.get("/api/occupations/29-1141.00").status_code == 404


def test_malay_example_has_an_explicit_keyword_alias(engine: Engine, settings: Settings) -> None:
    with httpx.Client(transport=Capture(fake_services([]))) as client:
        cat.refresh_catalogue(engine, client)
    found = detect(engine, settings, "Kerani akaun")
    assert found.matches[0].soc == "43-3031.00"
    assert "translation" in found.note and "fallback" in found.engine
