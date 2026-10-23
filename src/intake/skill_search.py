"""Map a person's free text (a task, a CV line) to the pack's canonical skills.

Primary: BGE-M3 embeddings served on our RunPod endpoint, cosine similarity to each skill.
Fallback: a small BM25 keyword ranking, used when RunPod is not configured, too slow (a GPU cold
start) or failing. Every result says which engine produced it, so a fallback is never presented
as the model's answer.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass

import httpx

from src.config import Settings
from src.pack import Pack

RUNPOD_URL = "https://api.runpod.ai/v2/{endpoint}/runsync"
# A page must not wait for a cold GPU: after this many seconds we answer with the fallback.
RUNPOD_TIME_BUDGET_SECONDS = 8.0
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
    response = client.post(
        RUNPOD_URL.format(endpoint=settings.runpod_endpoint_id),
        headers={"Authorization": f"Bearer {settings.runpod_api_key}"},
        json={"input": {"task": "embed", "texts": texts}},
        timeout=RUNPOD_TIME_BUDGET_SECONDS,
    )
    response.raise_for_status()
    body = response.json()
    output = body.get("output") or {}
    if body.get("status") != "COMPLETED" or "vectors" not in output:
        raise RuntimeError(f"RunPod job not completed in time (status {body.get('status')})")
    vectors: list[list[float]] = output["vectors"]
    return vectors


# Skill embeddings never change for a pack version, so they are computed once per process.
_SKILL_VECTORS: dict[str, list[float]] = {}


def search(
    pack: Pack,
    query: str,
    settings: Settings,
    client: httpx.Client | None = None,
    top_k: int = TOP_K,
) -> SearchResult:
    if not settings.runpod_configured:
        return SearchResult(
            bm25(pack, query, top_k), "BM25 keywords (fallback)", "RunPod is not configured"
        )
    own = client is None
    http = client or httpx.Client()
    try:
        cached = _SKILL_VECTORS
        missing = [sid for sid in pack.skills if sid not in cached]
        texts = [query] + [_skill_text(pack, sid) for sid in missing]
        vectors = _embed(settings, texts, http)
        cached.update(dict(zip(missing, vectors[1:], strict=True)))
        q = vectors[0]  # vectors are normalised, so the dot product is the cosine
        scored = sorted(
            (
                (sid, sum(a * b for a, b in zip(q, v, strict=True)))
                for sid, v in cached.items()
                if sid in pack.skills
            ),
            key=lambda kv: -kv[1],
        )
        hits = [SkillHit(sid, pack.skills[sid].name, round(s, 3)) for sid, s in scored[:top_k]]
        return SearchResult(hits, "bge-m3 (RunPod)", "")
    except (httpx.HTTPError, RuntimeError, ValueError, KeyError) as exc:
        return SearchResult(
            bm25(pack, query, top_k),
            "BM25 keywords (fallback)",
            f"RunPod unavailable: {type(exc).__name__}",
        )
    finally:
        if own:
            http.close()
