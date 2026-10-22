"""Search used by the running app: RunPod hybrid when configured and ready, BM25 otherwise.

Why a service and not the hybrid retriever directly: the GPU worker scales to zero, so the first
request after an idle period waits for a cold start (measured 98 s). A page cannot wait that long.
Each search therefore waits at most SEARCH_BUDGET_SECONDS for the hybrid result; if it is not
ready, the keyword (BM25) result is returned with a note saying so, and the hybrid job keeps
running in the background so the same search is answered by the GPU next time. Every response
says which engine produced it (`engine`), so a fallback is never presented as GPU search.

Document vectors are computed once per corpus and model, then cached in memory and on disk
(data/cache/, not committed), so a restart does not re-embed the corpus.
"""

import hashlib
import json
import logging
import threading
from collections.abc import Sequence
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from src.engine import params
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.hybrid import DenseRetriever, HybridRetriever
from src.retrieval.models import Document, SearchFilters, SearchResult
from src.retrieval.runpod_backends import (
    EMBEDDING_MODEL,
    RunPodBGEM3Embedder,
    RunPodBGEReranker,
    RunPodClient,
)

_log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"
# DECLARED: how long a page waits for GPU search before showing keyword results (seconds).
SEARCH_BUDGET_SECONDS = 15.0
# DECLARED: finished GPU results kept in memory (enough for a demo session).
RESULT_CACHE_SIZE = 256

Engine = Literal["hybrid", "keyword"]


class SearchResponse(BaseModel):
    query: str
    engine: Engine
    note: str
    results: list[SearchResult]


class CachedEmbedder:
    """Embeds the corpus once (memory + disk cache); queries always go to the backend."""

    def __init__(self, backend: RunPodBGEM3Embedder, cache_dir: Path = CACHE_DIR) -> None:
        self.backend = backend
        self.cache_dir = cache_dir

    def _path(self, texts: Sequence[str]) -> Path:
        digest = hashlib.sha256("\n".join([EMBEDDING_MODEL, *texts]).encode("utf-8")).hexdigest()
        return self.cache_dir / f"vectors_{digest[:16]}.json"

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if len(texts) == 1:
            return self.backend.embed(texts)
        path = self._path(texts)
        if path.exists():
            cached: list[list[float]] = json.loads(path.read_text(encoding="utf-8"))
            if len(cached) == len(texts):
                return cached
        vectors = self.backend.embed(texts)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(vectors), encoding="utf-8")
        return vectors


def _key(query: str, filters: SearchFilters | None, k: int) -> str:
    return json.dumps([query.strip().lower(), filters.model_dump() if filters else None, k])


class SearchService:
    def __init__(
        self,
        documents: Sequence[Document],
        client: RunPodClient | None = None,
        budget_seconds: float = SEARCH_BUDGET_SECONDS,
        cache_dir: Path = CACHE_DIR,
    ) -> None:
        self.documents = list(documents)
        self.client = client or RunPodClient()
        self.budget = budget_seconds
        self.keyword = BM25Retriever()
        self.keyword.index(self.documents)
        self._hybrid: HybridRetriever | None = None
        self._cache_dir = cache_dir
        self._lock = threading.Lock()
        self._results: dict[str, list[SearchResult]] = {}
        self._jobs: dict[str, Future[list[SearchResult]]] = {}
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="search")

    def _hybrid_retriever(self) -> HybridRetriever:
        with self._lock:
            if self._hybrid is None:
                embedder = CachedEmbedder(RunPodBGEM3Embedder(self.client), self._cache_dir)
                hybrid = HybridRetriever(
                    BM25Retriever(), DenseRetriever(embedder), RunPodBGEReranker(self.client)
                )
                hybrid.index(self.documents)
                self._hybrid = hybrid
            return self._hybrid

    def _run_hybrid(
        self, key: str, query: str, filters: SearchFilters | None, k: int
    ) -> list[SearchResult]:
        try:
            results = self._hybrid_retriever().search(query, filters, k)
            with self._lock:
                if len(self._results) >= RESULT_CACHE_SIZE:
                    self._results.pop(next(iter(self._results)))
                self._results[key] = results
            return results
        finally:
            with self._lock:
                self._jobs.pop(key, None)

    def keyword_search(
        self, query: str, filters: SearchFilters | None, k: int
    ) -> list[SearchResult]:
        return self.keyword.search(query, filters, k)

    def search(
        self, query: str, filters: SearchFilters | None = None, k: int = params.RETRIEVAL_TOP_K
    ) -> SearchResponse:
        if not self.client.configured:
            return SearchResponse(
                query=query,
                engine="keyword",
                note="Keyword search (BM25): GPU search is not configured.",
                results=self.keyword_search(query, filters, k),
            )
        key = _key(query, filters, k)
        with self._lock:
            cached = self._results.get(key)
            job = self._jobs.get(key)
            if cached is None and job is None:
                job = self._executor.submit(self._run_hybrid, key, query, filters, k)
                self._jobs[key] = job
        if cached is not None:
            return SearchResponse(query=query, engine="hybrid", note=HYBRID_NOTE, results=cached)
        assert job is not None
        try:
            results = job.result(timeout=self.budget)
        except FutureTimeout:
            note = (
                "Keyword search (BM25): the GPU worker is starting up, so keyword results are "
                "shown. Search again in a minute for GPU results."
            )
            return SearchResponse(
                query=query,
                engine="keyword",
                note=note,
                results=self.keyword_search(query, filters, k),
            )
        except Exception as error:  # noqa: BLE001 (any RunPod/HTTP failure → visible fallback)
            _log.warning("GPU search failed, using BM25: %s", error)
            return SearchResponse(
                query=query,
                engine="keyword",
                note=f"Keyword search (BM25): GPU search failed ({type(error).__name__}).",
                results=self.keyword_search(query, filters, k),
            )
        return SearchResponse(query=query, engine="hybrid", note=HYBRID_NOTE, results=results)


HYBRID_NOTE = "GPU search on RunPod: BGE-M3 embeddings + BM25 fused (RRF), then bge-reranker."
