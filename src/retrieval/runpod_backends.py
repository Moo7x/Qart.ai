"""RunPod backends for the hybrid retriever (BGE-M3 embeddings, bge-reranker-v2-m3 reranking).

The worker code is runpod/handler.py. These classes call it through RunPod's synchronous endpoint:
  POST https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync   (Authorization: Bearer {key})
  body {"input": {...}} → {"status": "COMPLETED", "output": {...}}
If the worker is still starting (a cold start loads both models, ~100 s), runsync answers
IN_QUEUE / IN_PROGRESS with a job id; the client then polls GET /v2/{endpoint}/status/{id} until
the job finishes or the overall wait runs out.
Credentials come only from the environment (RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID; names in
.env.example). Until both are set, every call raises RunPodNotConfiguredError, so nothing can
silently fall back to invented results. Nothing calls these yet: the planner still uses no
retrieval, and eval/retrieval_eval.py adds the hybrid row once the endpoint is configured.
"""

import os
import time
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import httpx

RUNPOD_API_KEY_ENV = "RUNPOD_API_KEY"
RUNPOD_ENDPOINT_ENV = "RUNPOD_ENDPOINT_ID"
RUNPOD_URL = "https://api.runpod.ai/v2/{endpoint}/runsync"
STATUS_URL = "https://api.runpod.ai/v2/{endpoint}/status/{job_id}"
EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
# DECLARED: a cold start loads two models (measured 98 s on the first request), so one HTTP call
# may take up to 120 s and the whole job, including polling, up to 300 s before giving up.
TIMEOUT_SECONDS = 120.0
MAX_WAIT_SECONDS = 300.0
POLL_SECONDS = 2.0  # DECLARED: status checks are cheap; 2 s keeps the extra wait small
COMPLETED = "COMPLETED"
PENDING = frozenset({"IN_QUEUE", "IN_PROGRESS"})


class RunPodNotConfiguredError(RuntimeError):
    """RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID is not set."""


class RunPodError(RuntimeError):
    """The endpoint answered, but not with a completed result."""


class RunPodClient:
    def __init__(
        self,
        env: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        source = os.environ if env is None else env
        self._api_key = source.get(RUNPOD_API_KEY_ENV, "").strip()
        self._endpoint = source.get(RUNPOD_ENDPOINT_ENV, "").strip()
        self._transport = transport
        self._sleep = sleep
        self._clock = clock

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self._endpoint)

    def run(self, job_input: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise RunPodNotConfiguredError(
                f"set {RUNPOD_API_KEY_ENV} and {RUNPOD_ENDPOINT_ENV} (see runpod/README.md)"
            )
        headers = {"Authorization": f"Bearer {self._api_key}"}
        deadline = self._clock() + MAX_WAIT_SECONDS
        with httpx.Client(transport=self._transport, timeout=TIMEOUT_SECONDS) as client:
            response = client.post(
                RUNPOD_URL.format(endpoint=self._endpoint),
                headers=headers,
                json={"input": job_input},
            )
            response.raise_for_status()
            body: dict[str, Any] = response.json()
            while body.get("status") in PENDING and body.get("id") and self._clock() < deadline:
                self._sleep(POLL_SECONDS)
                status_url = STATUS_URL.format(endpoint=self._endpoint, job_id=body["id"])
                polled = client.get(status_url, headers=headers)
                polled.raise_for_status()
                body = polled.json()
        output = body.get("output")
        if body.get("status") != COMPLETED or not isinstance(output, dict):
            raise RunPodError(f"RunPod job not completed (status {body.get('status')})")
        if "error" in output:
            raise RunPodError(f"worker rejected the job: {output['error']}")
        return output


class RunPodBGEM3Embedder:
    model = EMBEDDING_MODEL

    def __init__(self, client: RunPodClient | None = None) -> None:
        self.client = client or RunPodClient()

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = self.client.run({"task": "embed", "texts": list(texts)})[
            "vectors"
        ]
        return vectors


class RunPodBGEReranker:
    model = RERANKER_MODEL

    def __init__(self, client: RunPodClient | None = None) -> None:
        self.client = client or RunPodClient()

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        output = self.client.run({"task": "rerank", "query": query, "passages": list(passages)})
        scores: list[float] = output["scores"]
        return scores
