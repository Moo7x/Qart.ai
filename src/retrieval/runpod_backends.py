"""RunPod backends for the hybrid retriever (BGE-M3 embeddings, bge-reranker-v2-m3 reranking).

The worker code is runpod/handler.py. These classes call it through RunPod's synchronous endpoint:
  POST https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync   (Authorization: Bearer {key})
  body {"input": {...}} → {"status": "COMPLETED", "output": {...}}
Credentials come only from the environment (RUNPOD_API_KEY, RUNPOD_ENDPOINT_ID; names in
.env.example). Until both are set, every call raises RunPodNotConfiguredError, so nothing can
silently fall back to invented results. Nothing calls these yet: the planner still uses no
retrieval, and eval/retrieval_eval.py adds the hybrid row once the endpoint is configured.
"""

import os
from collections.abc import Mapping, Sequence
from typing import Any

import httpx

RUNPOD_API_KEY_ENV = "RUNPOD_API_KEY"
RUNPOD_ENDPOINT_ENV = "RUNPOD_ENDPOINT_ID"
RUNPOD_URL = "https://api.runpod.ai/v2/{endpoint}/runsync"
EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
# DECLARED: a cold start loads two models, so allow up to 120 s before giving up.
TIMEOUT_SECONDS = 120.0
COMPLETED = "COMPLETED"


class RunPodNotConfiguredError(RuntimeError):
    """RUNPOD_API_KEY or RUNPOD_ENDPOINT_ID is not set."""


class RunPodError(RuntimeError):
    """The endpoint answered, but not with a completed result."""


class RunPodClient:
    def __init__(
        self,
        env: Mapping[str, str] | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        source = os.environ if env is None else env
        self._api_key = source.get(RUNPOD_API_KEY_ENV, "").strip()
        self._endpoint = source.get(RUNPOD_ENDPOINT_ENV, "").strip()
        self._transport = transport

    @property
    def configured(self) -> bool:
        return bool(self._api_key and self._endpoint)

    def run(self, job_input: dict[str, Any]) -> dict[str, Any]:
        if not self.configured:
            raise RunPodNotConfiguredError(
                f"set {RUNPOD_API_KEY_ENV} and {RUNPOD_ENDPOINT_ENV} (see runpod/README.md)"
            )
        with httpx.Client(transport=self._transport, timeout=TIMEOUT_SECONDS) as client:
            response = client.post(
                RUNPOD_URL.format(endpoint=self._endpoint),
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={"input": job_input},
            )
        response.raise_for_status()
        body: dict[str, Any] = response.json()
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
