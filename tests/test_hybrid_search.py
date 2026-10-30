"""Hybrid occupation search: keyword and dense lists fused by rank, each fallback labelled."""

import json
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine

import src.occupations.catalogue  # noqa: F401  (registers the tables before init_db)
from src.config import Settings
from src.db import init_db, make_engine
from src.occupations import catalogue as cat
from src.occupations.detect import detect, rrf
from tests.test_occupations import Capture, fake_services, runpod_settings


@pytest.fixture(autouse=True)
def no_poll_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.runpod_jobs.POLL_SECONDS", 0.0)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    db = make_engine(f"sqlite:///{(tmp_path / 'h.sqlite').as_posix()}")
    init_db(db)
    return db


def test_rrf_rewards_agreement_and_keeps_either_list() -> None:
    fused = dict(rrf([["a", "b", "c"], ["b", "d"]], k=60))
    assert max(fused, key=lambda s: fused[s]) == "b"  # second and first: ahead of a single first
    assert set(fused) == {"a", "b", "c", "d"}  # nothing either method found is lost
    assert fused["a"] == pytest.approx(1 / 61) and fused["b"] == pytest.approx(1 / 62 + 1 / 61)


class FailRerank(httpx.MockTransport):
    """RunPod answers embedding jobs but every rerank job fails."""

    def __init__(self, inner: httpx.MockTransport) -> None:
        self.inner = inner
        self.rerank = False

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        if str(request.url).endswith("/run"):
            self.rerank = json.loads(request.content)["input"]["task"] == "rerank"
        if self.rerank and "/status/" in str(request.url):
            return httpx.Response(200, json={"id": "j", "status": "FAILED", "output": {}})
        return self.inner.handle_request(request)


def test_hybrid_reranks_and_names_every_engine(engine: Engine, settings: Settings) -> None:
    live = runpod_settings(settings)
    index = {"Bookkeeping, Accounting, and Auditing Clerks": 0, "Software Developers": 1}
    log: list[str] = []
    with httpx.Client(transport=Capture(fake_services(log, index))) as client:
        cat.refresh_catalogue(engine, client)
        cat.build_index(engine, live, client)
        found = detect(engine, live, "Accounts Clerk", client)
    assert found.engine.startswith("BM25 + ") and "reranker" in found.engine
    assert [s["name"] for s in found.stages][:4] == [
        "Embed your words on the GPU",
        "Compare with 3 occupations",
        "Keyword search over occupations",
        "Merge the two lists",
    ]


def test_a_failed_rerank_still_returns_the_merged_list_labelled(
    engine: Engine, settings: Settings
) -> None:
    live = runpod_settings(settings)
    index = {"Bookkeeping, Accounting, and Auditing Clerks": 0, "Software Developers": 1}
    with httpx.Client(transport=Capture(fake_services([], index))) as client:
        cat.refresh_catalogue(engine, client)
        cat.build_index(engine, live, client)
    with httpx.Client(transport=FailRerank(Capture(fake_services([], index)))) as client:
        found = detect(engine, live, "Accounts Clerk", client)
    assert "no re-rank" in found.engine and "re-ranker unavailable" in found.note
    assert found.matches and found.matches[0].soc == "43-3031.00"  # keyword + dense agree
