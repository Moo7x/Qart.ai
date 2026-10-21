"""CPU baseline: Okapi BM25 keyword search with metadata filters (no GPU, no LLM).

score(q, d) = Σ over query terms t of IDF(t) · f(t,d)·(k1 + 1) / (f(t,d) + k1·(1 − b + b·|d|/avgdl))
IDF(t)      = ln(1 + (N − n_t + 0.5) / (n_t + 0.5))
f(t,d) = term frequency in the document, |d| = document length in tokens, avgdl = mean length,
N = documents, n_t = documents containing t. k1 = 1.5, b = 0.75 (params.py, standard defaults).
"""

import math
import re
from collections import Counter
from collections.abc import Sequence

from src.engine import params
from src.retrieval.filters import passes
from src.retrieval.models import Document, SearchFilters, SearchResult

TOKEN = re.compile(r"[a-z0-9]+")
# A short English stop-word list: words that carry no topic and would add noise to BM25.
STOP_WORDS = frozenset(
    {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "i", "in", "into"}
    | {"is", "it", "of", "on", "or", "our", "that", "the", "their", "them", "this", "to", "use"}
    | {"using", "with", "you", "your"}
)


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN.findall(text.lower()) if t not in STOP_WORDS]


def searchable_text(document: Document) -> str:
    return f"{document.title} {document.text}"


def to_result(document: Document, score: float, rank: int, retriever: str) -> SearchResult:
    return SearchResult(
        document_id=document.id,
        kind=document.kind,
        title=document.title,
        score=score,
        rank=rank,
        source=document.source,
        url=document.url,
        date=document.date,
        retriever=retriever,
    )


class BM25Retriever:
    name = "bm25"

    def __init__(self, k1: float = params.BM25_K1, b: float = params.BM25_B) -> None:
        self.k1, self.b = k1, b
        self.documents: list[Document] = []
        self._term_counts: list[Counter[str]] = []
        self._lengths: list[int] = []
        self._document_frequency: Counter[str] = Counter()

    def index(self, documents: Sequence[Document]) -> None:
        self.documents = list(documents)
        self._term_counts = [Counter(tokenize(searchable_text(d))) for d in self.documents]
        self._lengths = [sum(c.values()) for c in self._term_counts]
        self._document_frequency = Counter()
        for counts in self._term_counts:
            self._document_frequency.update(counts.keys())

    def _idf(self, term: str) -> float:
        n_docs, n_term = len(self.documents), self._document_frequency[term]
        return math.log(1 + (n_docs - n_term + 0.5) / (n_term + 0.5))

    def score(self, query: str, position: int) -> float:
        counts, length = self._term_counts[position], self._lengths[position]
        average = sum(self._lengths) / len(self._lengths) if self._lengths else 0.0
        total = 0.0
        for term in tokenize(query):
            frequency = counts.get(term, 0)
            if not frequency:
                continue
            norm = self.k1 * (1 - self.b + self.b * length / average) if average else self.k1
            total += self._idf(term) * frequency * (self.k1 + 1) / (frequency + norm)
        return total

    def search(
        self, query: str, filters: SearchFilters | None = None, k: int = params.RETRIEVAL_TOP_K
    ) -> list[SearchResult]:
        scored = [
            (self.score(query, i), d) for i, d in enumerate(self.documents) if passes(d, filters)
        ]
        ranked = sorted((s for s in scored if s[0] > 0), key=lambda s: (-s[0], s[1].id))[:k]
        return [to_result(d, score, rank, self.name) for rank, (score, d) in enumerate(ranked, 1)]
