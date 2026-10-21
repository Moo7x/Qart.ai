"""Interfaces. The path planner and the companion will depend on `Retriever` only, so the CPU
baseline can later be swapped for the RunPod hybrid without changing callers."""

from collections.abc import Sequence
from typing import Protocol

from src.retrieval.models import Document, SearchFilters, SearchResult


class Retriever(Protocol):
    name: str

    def index(self, documents: Sequence[Document]) -> None:
        """Replace the indexed collection."""

    def search(
        self, query: str, filters: SearchFilters | None = None, k: int = ...
    ) -> list[SearchResult]:
        """Ranked results (best first) with source and date."""


class DenseEmbedder(Protocol):
    """Dense text embeddings (planned: BGE-M3 on RunPod)."""

    def embed(self, texts: Sequence[str]) -> list[list[float]]: ...


class Reranker(Protocol):
    """Cross-encoder relevance scores for (query, passage) pairs (planned: bge-reranker)."""

    def score(self, query: str, passages: Sequence[str]) -> list[float]: ...
