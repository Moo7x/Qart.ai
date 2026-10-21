"""RunPod backends for the hybrid retriever: interfaces only in this run (no calls are made).

Planned (PERSON_A Task A7): a RunPod serverless endpoint hosting BAAI/bge-m3 for embeddings and
BAAI/bge-reranker-v2-m3 for reranking, reached with RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID from the
environment. Until the endpoint exists these classes raise NotImplementedError, so nothing can
silently fall back to invented results.
"""

import os
from collections.abc import Sequence

RUNPOD_API_KEY_ENV = "RUNPOD_API_KEY"
RUNPOD_ENDPOINT_ENV = "RUNPOD_ENDPOINT_ID"
EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"


class _RunPodBackend:
    model: str

    def __init__(self) -> None:
        # Only whether a value exists is recorded; secrets are never stored or logged here.
        self.endpoint_configured = bool(os.environ.get(RUNPOD_ENDPOINT_ENV))

    def _not_connected(self) -> NotImplementedError:
        return NotImplementedError(
            f"{self.model} on RunPod is not connected yet (RAG preparation run; no GPU calls)"
        )


class RunPodBGEM3Embedder(_RunPodBackend):
    model = EMBEDDING_MODEL

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        raise self._not_connected()


class RunPodBGEReranker(_RunPodBackend):
    model = RERANKER_MODEL

    def score(self, query: str, passages: Sequence[str]) -> list[float]:
        raise self._not_connected()
