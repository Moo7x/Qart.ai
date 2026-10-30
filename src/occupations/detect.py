"""Match a job title or short description to standard O*NET occupations.

Primary (hybrid): BM25 keyword search and BGE-M3 dense search on RunPod each return their
HYBRID_CANDIDATES best occupations; reciprocal rank fusion merges the two lists (an occupation
high in either list rises; one high in both rises most), and the BGE cross-encoder reranker on
RunPod reorders the RERANK_CANDIDATES best of the fused list. Keyword search catches exact
titles and codes; dense search catches meaning, Malay and typos; the reranker reads query and
occupation text together.
Fallbacks, each labelled: the fused list without reranking when only the rerank job fails; BM25
alone when RunPod is not configured, cold beyond the budget, or has no index yet. Either way the
person confirms the occupation; a match is a suggestion, not a classification of the person.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy import Engine, select

from src.config import Settings
from src.evidence.field import field_profile
from src.occupations.catalogue import MODEL, catalogue, search_text, vector_table, vectors
from src.runpod_jobs import INTERACTIVE_BUDGET_SECONDS, RunPodError, embed, rerank
from src.stages import Stages

DENSE_CANDIDATES = 10  # dense-only shortlist (kept for the evaluation's dense+rerank baseline)
# Hybrid search. Each list contributes its 50 best occupations (about 5% of the 1,016), so a
# match one method ranks poorly can still be found by the other. RRF_K = 60 is the constant of
# the original reciprocal rank fusion paper (Cormack, Clarke & Büttcher 2009), not tuned here.
# The reranker scores the 10 best fused occupations: enough to recover a near miss, cheap to score.
HYBRID_CANDIDATES = 50
RRF_K = 60
RERANK_CANDIDATES = 10
SHOWN = 3
BM25_K1, BM25_B = 1.5, 0.75  # standard BM25 constants
TOKEN = re.compile(r"[a-z0-9]+")
# Team-reviewed bilingual example query, not a claim of complete Malay keyword coverage.
MALAY_QUERIES = {"kerani akaun": "accounts clerk"}


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
    stages: list[dict[str, Any]] = field(default_factory=list)  # measured, for the activity panel


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
        signature = (
            engine,
            tuple(
                conn.execute(
                    select(vector_table.c.soc, vector_table.c.text_hash)
                    .where(vector_table.c.model == MODEL)
                    .order_by(vector_table.c.soc)
                )
            ),
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


def rrf(rankings: list[list[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Reciprocal rank fusion: score(d) = Σ over lists of 1 / (k + rank of d in that list)."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, soc in enumerate(ranking, 1):
            scores[soc] = scores.get(soc, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda x: (-x[1], x[0]))


def keyword_query(query: str) -> str:
    """The query BM25 searches: a team-reviewed Malay example is translated, others as typed."""
    return MALAY_QUERIES.get(query.strip().lower(), query)


def detect(
    engine: Engine,
    settings: Settings,
    query: str,
    client: httpx.Client | None = None,
    use_reranker: bool = True,
) -> Detection:
    stages = Stages()
    rows = catalogue(engine)
    by_soc = {r["soc"]: r for r in rows}
    field_codes = field_profile().soc_codes()

    def result(engine_name: str, note: str, ranked: list[tuple[str, float]]) -> Detection:
        matches = [
            Match(soc, by_soc[soc]["title"], round(score, 4), soc in field_codes)
            for soc, score in ranked[:SHOWN]
        ]
        return Detection(query, engine_name, note, matches, stages.items)

    if not rows:
        return Detection(query, "none", "the occupation catalogue has not been collected yet")
    index = {soc: v for soc, v in _cached_vectors(engine).items() if soc in by_soc}
    if settings.runpod_configured and index:
        own = client is None
        http = client or httpx.Client(timeout=30)
        try:
            with stages.step("Embed your words on the GPU", "BGE-M3 on RunPod"):
                [qv] = embed(settings, [query], INTERACTIVE_BUDGET_SECONDS, http)
            with stages.step(f"Compare with {len(index)} occupations", "cosine similarity"):
                dense = dense_candidates(qv, index, HYBRID_CANDIDATES)
            with stages.step("Keyword search over occupations", "BM25"):
                keyword = bm25(rows, keyword_query(query), HYBRID_CANDIDATES)
            with stages.step("Merge the two lists", "reciprocal rank fusion"):
                fused = rrf([[s for s, _ in dense], [s for s, _ in keyword]])
            if not use_reranker:
                return result(f"BM25 + {MODEL} hybrid (RunPod)", "", fused)
            shortlist = [soc for soc, _ in fused[:RERANK_CANDIDATES]]
            passages = [search_text(by_soc[soc]) for soc in shortlist]
            try:
                with stages.step(f"Re-rank the best {len(passages)}", "bge-reranker on RunPod"):
                    scores = rerank(settings, query, passages, INTERACTIVE_BUDGET_SECONDS, http)
            except (RunPodError, httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                note = f"re-ranker unavailable ({type(exc).__name__}); merged list shown"
                return result(f"BM25 + {MODEL} hybrid (RunPod, no re-rank)", note, fused)
            ranked = sorted(zip(shortlist, scores, strict=True), key=lambda x: -x[1])
            return result(f"BM25 + {MODEL} hybrid + bge-reranker-v2-m3 (RunPod)", "", ranked)
        except (RunPodError, httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
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
    with stages.step("Keyword search over occupations", "BM25"):
        expanded = keyword_query(query)
        ranked_kw = bm25(rows, expanded, SHOWN)
    if expanded != query:
        note += "; team-reviewed example translation: accounts clerk"
    elif not ranked_kw:
        note += "; keyword fallback searches English titles. Try an English example."
    return result("BM25 keywords (fallback)", note, ranked_kw)
