"""Retrieval recall@5 on a small synthetic labelled set (RAG preparation, item 8e).

Run:  python -m eval.retrieval_eval   → rewrites the "retrieval" section of eval/RESULTS.md

recall@k(query) = |relevant ∩ top-k results| / |relevant|; the report gives the mean over queries
and the per-query hits, as counts. The RunPod hybrid (BGE-M3 embeddings + RRF + bge-reranker)
runs as a second row automatically once RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID are set, so the gain
is shown on the same set and corpus.
"""

import json
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from eval.results_md import RESULTS_PATH, write_section
from src.engine import params
from src.envfile import load_env_file
from src.retrieval.base import Retriever
from src.retrieval.bm25 import BM25Retriever
from src.retrieval.corpus import build_corpus
from src.retrieval.hybrid import DenseRetriever, HybridRetriever
from src.retrieval.models import Document
from src.retrieval.runpod_backends import RunPodBGEM3Embedder, RunPodBGEReranker, RunPodClient

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


def hybrid_row(results: Sequence[QueryResult] | None) -> str:
    name = "RunPod hybrid (BGE-M3 + RRF + bge-reranker)"
    if results is None:
        return (
            f"| {name} | not run | not run | set RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID "
            "(runpod/README.md) |"
        )
    hits, total = sum(r.hits for r in results), sum(r.relevant for r in results)
    return f"| {name} | {mean_recall(results):.2f} | {hits}/{total} | same set and corpus |"


def render(
    name: str,
    results: Sequence[QueryResult],
    corpus_size: int,
    k: int,
    hybrid: Sequence[QueryResult] | None = None,
) -> str:
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
        hybrid_row(hybrid),
        "",
        "| Query | Found (BM25) | Top 5 (BM25) |",
        "|---|---|---|",
    ]
    lines += [
        f"| {r.query_id} {r.query} | {r.hits}/{r.relevant} | {', '.join(r.retrieved) or '-'} |"
        for r in results
    ]
    return "\n".join(lines)


def run_hybrid(
    documents: Sequence[Document], k: int, client: RunPodClient | None = None
) -> list[QueryResult] | None:
    """Recall of the RunPod hybrid retriever, or None while RunPod is not configured."""
    runpod = client or RunPodClient()
    if not runpod.configured:
        return None
    hybrid = HybridRetriever(
        BM25Retriever(), DenseRetriever(RunPodBGEM3Embedder(runpod)), RunPodBGEReranker(runpod)
    )
    hybrid.index(documents)
    return recall_at_k(hybrid, load_set(), k)


def run(
    corpus: Sequence[Document] | None = None,
    results_path: Path = RESULTS_PATH,
    k: int = params.RETRIEVAL_TOP_K,
    client: RunPodClient | None = None,
) -> float:
    documents = list(corpus) if corpus is not None else build_corpus()
    retriever = BM25Retriever()
    retriever.index(documents)
    results = recall_at_k(retriever, load_set(), k)
    hybrid = run_hybrid(documents, k, client)
    text = render(retriever.name, results, len(documents), k, hybrid)
    write_section(SECTION, text, results_path)
    return mean_recall(results)


if __name__ == "__main__":
    load_env_file()  # RUNPOD_API_KEY / RUNPOD_ENDPOINT_ID from .env, if present
    print(f"BM25 mean recall@{params.RETRIEVAL_TOP_K}: {run():.2f}")
