"""RunPod serverless jobs (BGE-M3 embeddings and the BGE reranker, runpod/handler.py).

Jobs are submitted to the queue (/run) and polled (/status) until done or the time budget ends,
so a cold worker (about 13 s to start plus model loading, measured 24 Oct 2026) does not fail a
background job the way a short synchronous call did. Interactive callers pass a short budget and
keep their labelled fallback; background indexing passes a long one.
"""

import time
from typing import Any

import httpx

from src.config import Settings

API = "https://api.runpod.ai/v2/{endpoint}"
POLL_SECONDS = 2.0
DONE = {"COMPLETED", "FAILED", "CANCELLED", "TIMED_OUT"}
BACKGROUND_BUDGET_SECONDS = 240.0  # first job of a cold worker, with room for model loading
INTERACTIVE_BUDGET_SECONDS = 30.0  # a person waits for this; the page shows the stage
BATCH = 128  # texts per embedding job (the worker accepts up to 256)


class RunPodError(RuntimeError):
    """The job failed, was refused, or did not finish within the budget."""


def run_job(
    settings: Settings,
    payload: dict[str, Any],
    budget: float,
    client: httpx.Client,
    sleep: Any = time.sleep,
) -> dict[str, Any]:
    if not settings.runpod_configured:
        raise RunPodError("RunPod is not configured")
    base = API.format(endpoint=settings.runpod_endpoint_id)
    headers = {"Authorization": f"Bearer {settings.runpod_api_key}"}
    started = time.monotonic()
    submitted = client.post(f"{base}/run", headers=headers, json={"input": payload}, timeout=30)
    submitted.raise_for_status()
    job = submitted.json()
    while job.get("status") not in DONE:
        if time.monotonic() - started > budget:
            client.post(f"{base}/cancel/{job['id']}", headers=headers, timeout=10)
            raise RunPodError(f"job not finished within {budget:.0f} s")
        sleep(POLL_SECONDS)
        polled = client.get(f"{base}/status/{job['id']}", headers=headers, timeout=30)
        polled.raise_for_status()
        job = polled.json()
    output: dict[str, Any] = job.get("output") or {}
    if job["status"] != "COMPLETED" or "error" in output:
        raise RunPodError(f"job {job['status']}: {output.get('error', 'no output')}")
    return output


def embed(
    settings: Settings, texts: list[str], budget: float, client: httpx.Client
) -> list[list[float]]:
    vectors: list[list[float]] = []
    for start in range(0, len(texts), BATCH):
        out = run_job(
            settings, {"task": "embed", "texts": texts[start : start + BATCH]}, budget, client
        )
        vectors += out["vectors"]
    return vectors


def rerank(
    settings: Settings, query: str, passages: list[str], budget: float, client: httpx.Client
) -> list[float]:
    out = run_job(
        settings, {"task": "rerank", "query": query, "passages": passages}, budget, client
    )
    scores: list[float] = out["scores"]
    return scores
