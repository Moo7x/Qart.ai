"""Map a person's free text (a task, a CV line) to the pack's canonical skills.

Primary: BGE-M3 embeddings served on our RunPod endpoint, cosine similarity to each skill.
Fallback: a small BM25 keyword ranking, used when RunPod is not configured, too slow (a GPU cold
start) or failing. Every result says which engine produced it, so a fallback is never presented
as the model's answer.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

import httpx

from src.config import Settings
from src.pack import Pack
from src.runpod_jobs import INTERACTIVE_BUDGET_SECONDS, RunPodError, embed
from src.stages import Stages

# Shared async queue budget allows a cold worker to wake; no unbounded page wait.
RUNPOD_TIME_BUDGET_SECONDS = INTERACTIVE_BUDGET_SECONDS
TOP_K = 5
# BM25 constants (standard defaults from the information-retrieval literature).
BM25_K1 = 1.5
BM25_B = 0.75
TOKEN = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class SkillHit:
    skill: str
    name: str
    score: float


@dataclass(frozen=True)
class SearchResult:
    hits: list[SkillHit]
    engine: str  # "bge-m3 (RunPod)" or "BM25 keywords (fallback)"
    note: str
    stages: list[dict[str, Any]] = field(default_factory=list)


def _tokens(text: str) -> list[str]:
    return TOKEN.findall(text.lower())


def _skill_text(pack: Pack, skill_id: str) -> str:
    skill = pack.skills[skill_id]
    return f"{skill.name} {skill.id.replace('_', ' ')}"


def bm25(pack: Pack, query: str, top_k: int = TOP_K) -> list[SkillHit]:
    docs = {sid: _tokens(_skill_text(pack, sid)) for sid in pack.skills}
    avg_len = sum(len(d) for d in docs.values()) / len(docs)
    df = Counter(term for d in docs.values() for term in set(d))
    n = len(docs)
    scores = {}
    for sid, doc in docs.items():
        tf = Counter(doc)
        score = 0.0
        for term in set(_tokens(query)):
            if term not in tf:
                continue
            idf = math.log(1 + (n - df[term] + 0.5) / (df[term] + 0.5))
            norm = tf[term] + BM25_K1 * (1 - BM25_B + BM25_B * len(doc) / avg_len)
            score += idf * tf[term] * (BM25_K1 + 1) / norm
        if score > 0:
            scores[sid] = score
    best = sorted(scores.items(), key=lambda kv: -kv[1])[:top_k]
    return [SkillHit(sid, pack.skills[sid].name, round(s, 3)) for sid, s in best]


def _embed(settings: Settings, texts: list[str], client: httpx.Client) -> list[list[float]]:
    vectors = embed(settings, texts, RUNPOD_TIME_BUDGET_SECONDS, client)
    if len(vectors) != len(texts) or not vectors or not vectors[0]:
        raise ValueError("embedding count or dimension mismatch")
    dimension = len(vectors[0])
    if any(len(v) != dimension or not all(math.isfinite(x) for x in v) for v in vectors):
        raise ValueError("invalid embedding values")
    return vectors


# Skill embeddings never change for a pack version, so they are computed once per process.
_SKILL_VECTORS: dict[tuple[str, str], list[float]] = {}


def search(
    pack: Pack,
    query: str,
    settings: Settings,
    client: httpx.Client | None = None,
    top_k: int = TOP_K,
) -> SearchResult:
    stages = Stages()

    def fallback(note: str) -> SearchResult:
        with stages.step("Search canonical skill names", "BM25 keywords (fallback)"):
            hits = bm25(pack, query, top_k)
        return SearchResult(hits, "BM25 keywords (fallback)", note, stages.items)

    if not settings.runpod_configured:
        return fallback("RunPod is not configured; keyword suggestions need your confirmation.")
    own = client is None
    http = client or httpx.Client()
    try:
        cached = _SKILL_VECTORS
        keys = {sid: (sid, _skill_text(pack, sid)) for sid in pack.skills}
        missing = [sid for sid in pack.skills if keys[sid] not in cached]
        texts = [query] + [_skill_text(pack, sid) for sid in missing]
        with stages.step("Embed your tasks and uncached skills", "BGE-M3 on RunPod async queue"):
            vectors = _embed(settings, texts, http)
        cached.update(dict(zip([keys[sid] for sid in missing], vectors[1:], strict=True)))
        q = vectors[0]  # vectors are normalised, so the dot product is the cosine
        scored = sorted(
            (
                (sid, sum(a * b for a, b in zip(q, cached[key], strict=True)))
                for sid, key in keys.items()
            ),
            key=lambda kv: -kv[1],
        )
        hits = [SkillHit(sid, pack.skills[sid].name, round(s, 3)) for sid, s in scored[:top_k]]
        return SearchResult(
            hits, "bge-m3 (RunPod)", "Choose relevant skills, then set your level.", stages.items
        )
    except (httpx.HTTPError, RunPodError, ValueError, KeyError, TypeError) as exc:
        return fallback(f"RunPod unavailable: {type(exc).__name__}; keyword search used.")
    finally:
        if own:
            http.close()
