"""RunPod client (fake HTTP transport, no network) and worker logic (fake models, no GPU)."""

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

import httpx
import pytest

from src.retrieval.runpod_backends import (
    RunPodBGEM3Embedder,
    RunPodBGEReranker,
    RunPodClient,
    RunPodError,
)

ENV = {"RUNPOD_API_KEY": "test-key", "RUNPOD_ENDPOINT_ID": "endpoint123"}
HANDLER = Path(__file__).resolve().parent.parent / "runpod" / "handler.py"


def fake_runpod(output: dict[str, Any], status: str = "COMPLETED") -> httpx.MockTransport:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v2/endpoint123/runsync"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert "input" in json.loads(request.content)
        return httpx.Response(200, json={"status": status, "output": output})

    return httpx.MockTransport(respond)


def test_embedder_and_reranker_call_the_runsync_endpoint() -> None:
    embed_client = RunPodClient(ENV, fake_runpod({"vectors": [[0.1, 0.2]]}))
    assert RunPodBGEM3Embedder(embed_client).embed(["text"]) == [[0.1, 0.2]]
    rerank_client = RunPodClient(ENV, fake_runpod({"scores": [0.9]}))
    assert RunPodBGEReranker(rerank_client).score("q", ["p"]) == [0.9]


def test_incomplete_or_rejected_jobs_raise() -> None:
    with pytest.raises(RunPodError, match="not completed"):
        RunPodClient(ENV, fake_runpod({}, status="IN_QUEUE")).run({"task": "embed"})
    with pytest.raises(RunPodError, match="rejected"):
        RunPodClient(ENV, fake_runpod({"error": "bad input"})).run({"task": "embed"})


def load_handler() -> ModuleType:
    spec = importlib.util.spec_from_file_location("qart_runpod_handler", HANDLER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_worker_dispatches_and_validates_without_loading_models() -> None:
    worker = load_handler()

    def embed(texts: list[str]) -> list[list[float]]:
        return [[float(len(t))] for t in texts]

    def rerank(query: str, passages: list[str]) -> list[float]:
        return [1.0 for _ in passages]

    assert worker.handle({"task": "embed", "texts": ["ab"]}, embed, rerank)["vectors"] == [[2.0]]
    out = worker.handle({"task": "rerank", "query": "q", "passages": ["a", "b"]}, embed, rerank)
    assert out["scores"] == [1.0, 1.0] and out["model"] == "BAAI/bge-reranker-v2-m3"
    assert "error" in worker.handle({"task": "embed", "texts": []}, embed, rerank)
    assert "error" in worker.handle(
        {"task": "rerank", "query": "", "passages": ["a"]}, embed, rerank
    )
    assert "error" in worker.handle({"task": "translate"}, embed, rerank)


def test_retrieval_eval_adds_the_hybrid_row_when_runpod_is_configured(tmp_path: Path) -> None:
    from eval.retrieval_eval import run

    vocabulary = ("sql", "forecast", "control", "bank", "data")

    def respond(request: httpx.Request) -> httpx.Response:
        job = json.loads(request.content)["input"]
        if job["task"] == "embed":
            vectors = [[float(w in t.lower()) + 0.01 for w in vocabulary] for t in job["texts"]]
            return httpx.Response(200, json={"status": "COMPLETED", "output": {"vectors": vectors}})
        scores = [float(len(p)) for p in job["passages"]]
        return httpx.Response(200, json={"status": "COMPLETED", "output": {"scores": scores}})

    results = tmp_path / "RESULTS.md"
    run(results_path=results, client=RunPodClient(ENV, httpx.MockTransport(respond)))
    row = next(line for line in results.read_text("utf-8").splitlines() if "RunPod hybrid" in line)
    assert "not run" not in row and "same set and corpus" in row
