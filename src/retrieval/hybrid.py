"""Dense retrieval, reciprocal-rank fusion and optional reranking (hybrid search).

These classes work with any `DenseEmbedder` / `Reranker`; the planned backends are BGE-M3 and
bge-reranker on RunPod (src/retrieval/runpod_backends.py, interfaces only in this run).

Reciprocal-rank fusion: RRF(d) = Σ over rankings of 1 / (k + rank(d)), k = 60 (params.py). It
combines rankings without needing comparable scores (BM25 scores and cosine similarities are not).
"""

import math
from collections.abc import Sequence

from src.engine import params
from src.retrieval.base import DenseEmbedder, Reranker, Retriever
from src.retrieval.bm25 import searchable_text, to_result
from src.retrieval.filters import passes
from src.retrieval.models import Document, SearchFilters, SearchResult

# DECLARED: how many fused candidates are passed to the reranker (4 × the results returned).
CANDIDATE_POOL_FACTOR = 4


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[str]], k: int = params.RRF_K
) -> list[tuple[str, float]]:
    """Fuse ranked id lists (best first) into one list of (id, RRF score), best first."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))


def cosine(a: Sequence[float], b: Sequence[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


class DenseRetriever:
    name = "dense"

    def __init__(self, embedder: DenseEmbedder) -> None:
        self.embedder = embedder
        self.documents: list[Document] = []
        self._vectors: list[list[float]] = []

    def index(self, documents: Sequence[Document]) -> None:
        self.documents = list(documents)
        self._vectors = self.embedder.embed([searchable_text(d) for d in self.documents])

    def search(
        self, query: str, filters: SearchFilters | None = None, k: int = params.RETRIEVAL_TOP_K
    ) -> list[SearchResult]:
        query_vector = self.embedder.embed([query])[0]
        scored = [
            (cosine(query_vector, v), d)
            for v, d in zip(self._vectors, self.documents, strict=True)
            if passes(d, filters)
        ]
        ranked = sorted(scored, key=lambda s: (-s[0], s[1].id))[:k]
        return [to_result(d, score, rank, self.name) for rank, (score, d) in enumerate(ranked, 1)]


class HybridRetriever:
    """BM25 + dense via reciprocal-rank fusion, then an optional cross-encoder rerank."""

    def __init__(
        self, keyword: Retriever, dense: Retriever, reranker: Reranker | None = None
    ) -> None:
        self.keyword, self.dense, self.reranker = keyword, dense, reranker
        self.name = "hybrid-rrf+rerank" if reranker else "hybrid-rrf"
        self.documents: dict[str, Document] = {}

    def index(self, documents: Sequence[Document]) -> None:
        self.documents = {d.id: d for d in documents}
        self.keyword.index(documents)
        self.dense.index(documents)

    def search(
        self, query: str, filters: SearchFilters | None = None, k: int = params.RETRIEVAL_TOP_K
    ) -> list[SearchResult]:
        pool = CANDIDATE_POOL_FACTOR * k
        rankings = [
            [r.document_id for r in retriever.search(query, filters, pool)]
            for retriever in (self.keyword, self.dense)
        ]
        fused = reciprocal_rank_fusion(rankings)[:pool]
        if self.reranker is not None and fused:
            ids = [doc_id for doc_id, _ in fused]
            scores = self.reranker.score(query, [searchable_text(self.documents[i]) for i in ids])
            fused = sorted(zip(ids, scores, strict=True), key=lambda item: (-item[1], item[0]))
        return [
            to_result(self.documents[doc_id], score, rank, self.name)
            for rank, (doc_id, score) in enumerate(fused[:k], start=1)
        ]
