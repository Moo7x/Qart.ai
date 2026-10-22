"""Search used by the app: hybrid when RunPod answers in time, labelled BM25 fallback otherwise."""

import json
import threading
from pathlib import Path
from typing import Any

import httpx
from fastapi.testclient import TestClient

from src.retrieval.models import Document, SearchFilters
from src.retrieval.runpod_backends import RunPodClient
from src.retrieval.service import SearchService

ENV = {"RUNPOD_API_KEY": "test-key", "RUNPOD_ENDPOINT_ID": "endpoint123"}


def docs() -> list[Document]:
    def doc(i: str, kind: Any, title: str) -> Document:
        return Document(
            id=i, kind=kind, title=title, text=title, source="test", url="https://x", date="2026"
        )

    return [
        doc("c1", "course", "Bank reconciliation basics"),
        doc("c2", "course", "Forecasting with spreadsheets"),
        doc("t1", "onet_task", "Reconcile bank statements to the ledger"),
    ]


class FakeRunPod:
    """Answers embed/rerank jobs; counts calls; can block or fail."""

    def __init__(self, gate: threading.Event | None = None, fail: bool = False) -> None:
        self.embedded_texts = 0
        self.calls = 0
        self.gate = gate
        self.fail = fail

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls += 1
        if self.gate is not None:
            self.gate.wait(5)
        if self.fail:
            return httpx.Response(500)
        job = json.loads(request.content)["input"]
        if job["task"] == "embed":
            self.embedded_texts += len(job["texts"])
            vectors = [
                [1.0, float("bank" in t.lower()), float("forecast" in t.lower())]
                for t in job["texts"]
            ]
            output: dict[str, Any] = {"vectors": vectors}
        else:
            query = set(job["query"].lower().split())
            output = {"scores": [len(query & set(p.lower().split())) for p in job["passages"]]}
        return httpx.Response(200, json={"status": "COMPLETED", "output": output})


def service(fake: FakeRunPod, tmp_path: Path, budget: float = 5.0) -> SearchService:
    client = RunPodClient(ENV, httpx.MockTransport(fake))
    return SearchService(docs(), client, budget_seconds=budget, cache_dir=tmp_path)


def test_without_runpod_keyword_search_is_used_and_labelled(tmp_path: Path) -> None:
    result = SearchService(docs(), RunPodClient({}), cache_dir=tmp_path).search("bank ledger")
    assert result.engine == "keyword" and "not configured" in result.note
    assert result.results[0].document_id in {"c1", "t1"}


def test_hybrid_results_are_used_and_cached(tmp_path: Path) -> None:
    fake = FakeRunPod()
    search = service(fake, tmp_path)
    first = search.search("bank reconciliation", SearchFilters(kinds=["course"]), 2)
    assert first.engine == "hybrid" and first.results[0].document_id == "c1"
    assert all(r.kind == "course" for r in first.results)
    calls = fake.calls
    again = search.search("bank reconciliation", SearchFilters(kinds=["course"]), 2)
    assert again.engine == "hybrid" and fake.calls == calls  # served from the result cache


def test_a_cold_start_shows_keyword_results_then_gpu_results(tmp_path: Path) -> None:
    gate = threading.Event()
    fake = FakeRunPod(gate)
    search = service(fake, tmp_path, budget=0.05)
    slow = search.search("bank reconciliation")
    assert slow.engine == "keyword" and "starting up" in slow.note
    gate.set()
    search._jobs and next(iter(search._jobs.values())).result(5)  # let the background job finish
    assert search.search("bank reconciliation").engine == "hybrid"


def test_a_failing_endpoint_falls_back_visibly(tmp_path: Path) -> None:
    result = service(FakeRunPod(fail=True), tmp_path).search("bank reconciliation")
    assert result.engine == "keyword" and "failed" in result.note and result.results


def test_corpus_vectors_are_cached_on_disk(tmp_path: Path) -> None:
    first = FakeRunPod()
    service(first, tmp_path).search("bank")
    assert first.embedded_texts == len(docs()) + 1  # corpus + query
    second = FakeRunPod()
    service(second, tmp_path).search("forecast")
    assert second.embedded_texts == 1  # only the query: corpus vectors came from disk


def test_search_routes(client: TestClient) -> None:
    found = client.get("/api/search", params={"q": "reconcile bank statements"}).json()
    assert found["engine"] == "keyword" and found["results"]
    courses = client.get("/api/resources/unsupported_adjustment").json()
    assert courses["results"] and all(r["kind"] == "course" for r in courses["results"])
    assert client.get("/api/resources/no_such_skill").status_code == 404
    assert client.get("/api/search", params={"q": "x"}).status_code == 422
