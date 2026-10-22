"""RunPod serverless worker for Qart.ai retrieval (PERSON_A Task A7).

Serves two models on one GPU endpoint:
- BAAI/bge-m3 (MIT): dense text embeddings, normalised, for the hybrid retriever;
- BAAI/bge-reranker-v2-m3 (Apache-2.0): cross-encoder relevance scores for reranking.

Job input → output:
  {"task": "embed", "texts": ["...", ...]}  → {"vectors": [[...], ...], "model": ...}
  {"task": "rerank", "query": "...", "passages": ["...", ...]} → {"scores": [...], "model": ...}
Bad input returns {"error": "..."} instead of raising, so the caller sees why.

Deploy: see runpod/README.md. Models load once per worker (first job pays the cold start).
"""

from collections.abc import Callable, Sequence
from typing import Any

EMBEDDING_MODEL = "BAAI/bge-m3"
RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"
# Guards against runaway cost: at most 256 texts and 8,000 characters each per job.
MAX_TEXTS = 256
MAX_CHARS = 8000

Embed = Callable[[Sequence[str]], list[list[float]]]
Rerank = Callable[[str, Sequence[str]], list[float]]

_models: dict[str, Any] = {}


def _embed(texts: Sequence[str]) -> list[list[float]]:
    if "embedder" not in _models:
        from sentence_transformers import SentenceTransformer

        _models["embedder"] = SentenceTransformer(EMBEDDING_MODEL)
    vectors = _models["embedder"].encode(list(texts), normalize_embeddings=True)
    return [list(map(float, v)) for v in vectors]


def _rerank(query: str, passages: Sequence[str]) -> list[float]:
    if "reranker" not in _models:
        from sentence_transformers import CrossEncoder

        _models["reranker"] = CrossEncoder(RERANKER_MODEL)
    scores = _models["reranker"].predict([(query, p) for p in passages])
    return [float(s) for s in scores]


def _texts_ok(texts: Any) -> bool:
    return (
        isinstance(texts, list)
        and 0 < len(texts) <= MAX_TEXTS
        and all(isinstance(t, str) and len(t) <= MAX_CHARS for t in texts)
    )


def handle(job_input: dict[str, Any], embed: Embed, rerank: Rerank) -> dict[str, Any]:
    """Validate one job and dispatch it (model functions are passed in so tests need no GPU)."""
    task = job_input.get("task")
    if task == "embed":
        texts = job_input.get("texts")
        if not _texts_ok(texts):
            return {"error": f"texts must be 1–{MAX_TEXTS} strings of ≤{MAX_CHARS} characters"}
        return {"vectors": embed(texts), "model": EMBEDDING_MODEL}
    if task == "rerank":
        query, passages = job_input.get("query"), job_input.get("passages")
        if not isinstance(query, str) or not query or not _texts_ok(passages):
            return {"error": "rerank needs a non-empty query and 1–256 passages"}
        return {"scores": rerank(query, passages), "model": RERANKER_MODEL}
    return {"error": "task must be 'embed' or 'rerank'"}


def handler(job: dict[str, Any]) -> dict[str, Any]:
    return handle(job.get("input", {}), _embed, _rerank)


if __name__ == "__main__":
    import runpod

    runpod.serverless.start({"handler": handler})
