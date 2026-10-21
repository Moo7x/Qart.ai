"""Retrieval recall@5 on a small synthetic labelled set (RAG preparation, item 8e).

Run:  python -m eval.retrieval_eval   → rewrites the "retrieval" section of eval/RESULTS.md

recall@k(query) = |relevant ∩ top-k results| / |relevant|; the report gives the mean over queries
and the per-query hits, as counts. Today only the CPU BM25 baseline runs; the RunPod hybrid
(BGE-M3 embeddings + RRF + bge-reranker) will be added as a second row once it is connected, so
the gain can be shown on the same set.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.results_md import RESULTS_PATH, write_section
from src.engine import params
from src.retrieval.base import Retriever
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.corpus import build_corpus
from src.retrieval.models import Document

SET_PATH = Path(__file__).resolve().parent / "retrieval_set.json"
SECTION = "retrieval"


@dataclass(frozen=True)
class QueryResult:
    query_id: str
    query: str
    hits: int
    relevant: int
    retrieved: list[str]


def load_set(path: Path = SET_PATH) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = json.loads(path.read_text(encoding="utf-8"))["queries"]
    return queries


def recall_at_k(
    retriever: Retriever, queries: Sequence[dict[str, Any]], k: int = params.RETRIEVAL_TOP_K
) -> list[QueryResult]:
    results = []
    for q in queries:
        top = [r.document_id for r in retriever.search(q["query"], None, k)]
        relevant = set(q["relevant"])
        results.append(
            QueryResult(q["id"], q["query"], len(relevant & set(top)), len(relevant), top)
        )
    return results


def mean_recall(results: Sequence[QueryResult]) -> float:
    return sum(r.hits / r.relevant for r in results) / len(results) if results else 0.0


def render(name: str, results: Sequence[QueryResult], corpus_size: int, k: int) -> str:
    hits = sum(r.hits for r in results)
    total = sum(r.relevant for r in results)
    lines = [
        f"## Retrieval recall@{k} (synthetic labelled set)",
        "",
        f"Set: `eval/retrieval_set.json` ({len(results)} queries, labelled synthetic). Corpus: "
        f"{corpus_size} documents (verified courses + O*NET 31.0 tasks and DWAs for our roles).",
        "",
        "| Retriever | Mean recall@5 | Relevant found | Notes |",
        "|---|---|---|---|",
        f"| {name} (CPU baseline) | {mean_recall(results):.2f} | {hits}/{total} | "
        f"k1={params.BM25_K1}, b={params.BM25_B}, not tuned |",
        "| RunPod hybrid (BGE-M3 + RRF + bge-reranker) | not run | not run | backend not "
        "connected yet |",
        "",
        "| Query | Found | Top 5 |",
        "|---|---|---|",
    ]
    lines += [
        f"| {r.query_id} {r.query} | {r.hits}/{r.relevant} | {', '.join(r.retrieved) or '-'} |"
        for r in results
    ]
    return "\n".join(lines)


def run(
    corpus: Sequence[Document] | None = None,
    results_path: Path = RESULTS_PATH,
    k: int = params.RETRIEVAL_TOP_K,
) -> float:
    documents = list(corpus) if corpus is not None else build_corpus()
    retriever = BM25Retriever()
    retriever.index(documents)
    results = recall_at_k(retriever, load_set(), k)
    write_section(SECTION, render(retriever.name, results, len(documents), k), results_path)
    return mean_recall(results)


if __name__ == "__main__":
    print(f"BM25 mean recall@{params.RETRIEVAL_TOP_K}: {run():.2f}")
