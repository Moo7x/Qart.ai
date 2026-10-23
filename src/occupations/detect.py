"""Match a job title or short description to standard O*NET occupations.

Primary: embed the query with BGE-M3 on RunPod, take the DENSE_CANDIDATES most similar
occupations (cosine; vectors are normalised), then reorder them with the BGE cross-encoder
reranker on RunPod. Fallback (RunPod not configured, cold beyond the budget, or no index yet):
BM25 keyword search over the same occupation texts, labelled as such. Either way the person
confirms the occupation; a match is a suggestion, not a classification of the person.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy import Engine, func, select

from src.config import Settings
from src.evidence.field import field_profile
from src.occupations.catalogue import MODEL, catalogue, search_text, vector_table, vectors
from src.runpod_jobs import INTERACTIVE_BUDGET_SECONDS, RunPodError, embed, rerank

DENSE_CANDIDATES = 10  # passed to the reranker: enough to recover a near miss, cheap to score
SHOWN = 3
BM25_K1, BM25_B = 1.5, 0.75  # standard BM25 constants
TOKEN = re.compile(r"[a-z0-9]+")


@dataclass
class Match:
    soc: str
    title: str
    score: float
    in_field: bool  # one of the GBS finance occupations with full journeys


@dataclass
class Detection:
    query: str
    engine: str
    note: str
    matches: list[Match] = field(default_factory=list)


def _tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def bm25(rows: list[dict[str, Any]], query: str, top: int) -> list[tuple[str, float]]:
    docs = {r["soc"]: _tokens(search_text(r)) for r in rows}
    n = len(docs)
    avg = sum(len(d) for d in docs.values()) / n if n else 0
    df: Counter[str] = Counter(t for d in docs.values() for t in set(d))
    q = _tokens(query)
    scores = []
    for soc, words in docs.items():
        tf = Counter(words)
        s = 0.0
        for term in q:
            if term in tf:
                idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
                s += (
                    idf
                    * tf[term]
                    * (BM25_K1 + 1)
                    / (tf[term] + BM25_K1 * (1 - BM25_B + BM25_B * len(words) / avg))
                )
        scores.append((soc, s))
    scores.sort(key=lambda x: -x[1])
    return [x for x in scores[:top] if x[1] > 0]


_CACHE: dict[str, Any] = {}


def _cached_vectors(engine: Engine) -> dict[str, list[float]]:
    """Vectors from the database, reloaded only when the stored set changes."""
    with engine.connect() as conn:
        signature = tuple(
            conn.execute(
                select(func.count(), func.max(vector_table.c.text_hash)).where(
                    vector_table.c.model == MODEL
                )
            ).one()
        )
    if _CACHE.get("signature") != signature:
        _CACHE["signature"], _CACHE["vectors"] = signature, vectors(engine)
    found: dict[str, list[float]] = _CACHE["vectors"]
    return found


def dense_candidates(
    query_vector: list[float], index: dict[str, list[float]], top: int
) -> list[tuple[str, float]]:
    scored = [
        (soc, sum(a * b for a, b in zip(query_vector, v, strict=True))) for soc, v in index.items()
    ]
    scored.sort(key=lambda x: -x[1])
    return scored[:top]


def detect(
    engine: Engine,
    settings: Settings,
    query: str,
    client: httpx.Client | None = None,
    use_reranker: bool = True,
) -> Detection:
    rows = catalogue(engine)
    by_soc = {r["soc"]: r for r in rows}
    field_codes = field_profile().soc_codes()

    def result(engine_name: str, note: str, ranked: list[tuple[str, float]]) -> Detection:
        matches = [
            Match(soc, by_soc[soc]["title"], round(score, 4), soc in field_codes)
            for soc, score in ranked[:SHOWN]
        ]
        return Detection(query, engine_name, note, matches)

    if not rows:
        return Detection(query, "none", "the occupation catalogue has not been collected yet")
    index = _cached_vectors(engine)
    if settings.runpod_configured and index:
        own = client is None
        http = client or httpx.Client(timeout=30)
        try:
            [qv] = embed(settings, [query], INTERACTIVE_BUDGET_SECONDS, http)
            dense = dense_candidates(qv, index, DENSE_CANDIDATES)
            if not use_reranker:
                return result(f"{MODEL} dense (RunPod)", "", dense)
            passages = [search_text(by_soc[soc]) for soc, _ in dense]
            scores = rerank(settings, query, passages, INTERACTIVE_BUDGET_SECONDS, http)
            ranked = sorted(zip([s for s, _ in dense], scores, strict=True), key=lambda x: -x[1])
            return result(f"{MODEL} + bge-reranker-v2-m3 (RunPod)", "", ranked)
        except (RunPodError, httpx.HTTPError) as exc:
            note = f"RunPod unavailable ({type(exc).__name__}); keyword search used"
        finally:
            if own:
                http.close()
    else:
        note = (
            "no RunPod index yet; keyword search used"
            if settings.runpod_configured
            else "RunPod not configured; keyword search used"
        )
    return result("BM25 keywords (fallback)", note, bm25(rows, query, SHOWN))
